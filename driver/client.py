import os
import logging
import time
from openai import OpenAI
import requests
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta
import json
logger = logging.getLogger(__name__)

# Type alias for completion strategy functions
CompletionStrategy = Callable[[str, Optional[str], float, int], Dict[str, any]]

class AIClient:
    def __init__(self, client_type='ollama', model=None):
        """Initialize AI client wrapper for either OpenAI or Ollama

        Args:
            client_type (str): Type of client - 'ollama' or 'openai'
            model (str): Model name to use
        """
        if model is not None:
            self.model = model
        
        match client_type.lower():
            case 'openai':
                try:
                    api_key = os.environ["OPENAI_API_KEY"]
                    if not hasattr(self, 'model') or self.model is None:
                        self.model = 'gpt-4o'
                    client = OpenAI(api_key=api_key)
                    self.strategy = self._create_openai_strategy(client)
                except KeyError:
                    raise ValueError("OPENAI_API_KEY environment variable must be set for OpenAI client")
            case 'ollama':
                if not hasattr(self, 'model') or self.model is None:
                    self.model = 'llama3.1'
                self.strategy = self._create_ollama_strategy("http://localhost:11434/api")
            case _:
                raise ValueError(f"Unsupported client type: {client_type}")

    def _create_openai_strategy(self, client: OpenAI) -> CompletionStrategy:
        """Creates an OpenAI completion strategy function"""
        def _apply_rate_limiting(tokens_used: int):
            # Initialize rate limiting state if not exists
            if not hasattr(self, '_last_request_time'):
                self._last_request_time = datetime.now()
                self._token_bucket = 10000  # Max bucket size
            
            # Calculate tokens to add based on time elapsed
            now = datetime.now()
            time_elapsed = (now - self._last_request_time).total_seconds()
            tokens_to_add = time_elapsed * (10000 / 60)  # Refill rate: 10k tokens/min
            
            self._token_bucket = min(10000, self._token_bucket + tokens_to_add)
            
            # Wait if needed
            if self._token_bucket < tokens_used:
                wait_time = (tokens_used - self._token_bucket) * (60 / 10000)
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self._token_bucket = 10000
            
            # Update state
            self._token_bucket -= tokens_used
            self._last_request_time = now
            
        def generate(prompt: str, system_prompt: str = None, 
                    temperature: float = 0.7, max_tokens: int = 500) -> dict:
            logger.info(f"Generating completion with OPENAI and model {self.model}")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            _apply_rate_limiting(response.usage.total_tokens)
            return {
                'content': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens
            }
        
        return generate

    def _create_ollama_strategy(self, base_url: str) -> CompletionStrategy:
        """Creates an Ollama completion strategy function"""
        def generate(prompt: str, system_prompt: str = None, 
                    temperature: float = 0.7, max_tokens: int = 500) -> dict:
            logger.info(f"Generating completion with OLLAMA and model {self.model}")
            logger.debug(f'System prompt: {system_prompt}')
            logger.debug(f'User prompt: {prompt}')
            payload = {
                'model': self.model,
                'prompt': prompt,
                'system': system_prompt if system_prompt else '',
                'temperature': temperature
            }
            
            response = requests.post(f"{base_url}/generate", json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            logger.debug(f'Response: {response.text}')
            # Combine all response chunks
            full_response = ""
            for line in response.text.strip().split('\n'):
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        full_response += chunk.get('response', '')
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse response chunk: {line}")
                        continue
            
            return {
                'content': full_response,
                'tokens_used': None  # Ollama doesn't provide token count
            }
        
        return generate


    def generate_completion(self, prompt: str, system_prompt: str = None, 
                          temperature: float = 0.7, max_tokens: int = 500) -> dict:
        """Generate completion for given prompt

        Args:
            prompt (str): The prompt to generate completion for
            system_prompt (str, optional): System prompt for context
            temperature (float, optional): Sampling temperature
            max_tokens (int, optional): Maximum tokens in response

        Returns:
            dict: Response containing generated text and metadata
        """
        try:
            return self.strategy(prompt, system_prompt, temperature, max_tokens)
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            raise



