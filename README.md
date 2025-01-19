# Introduction

Curator is a tool that helps you to scrape and summarize social media posts. Currently it supports Substack.
The workflow is as follows:
1. Scrape posts from a Substack blog. The step is called "scrape"
2. Summarize the posts. The step is called "summarize"
3. Generate a summary of the blog. The step is called "generate"

# User Manual

You can use it as a library or as a command line tool. As a command line tool you can run all the steps at once or only selected steps.

Usage:
Run the first step to scrape posts from a Substack blog.
```
curator --steps scrape  --posts_to_scrape 3
```
The posts_to_scrape switch is optional and contains the number of posts to scrape. This is useful if you want to only test a couple of posts for testing purposes.

Run the second step to summarize the posts.
```
curator --steps summarize  --posts_to_summarize 3 --client openai
```
The posts_to_summarize switch is optional and contains the number of posts to summarize. This is useful if you want to only test a couple of posts for testing purposes.
The client switch is optional and contains the client to use. The default is ollama. You can also use openai. If you don't have local ollama instance you must use the openai client.

Run the third step to generate a summary of the blog.
```
curator --steps generate  --posts_to_generate 3
```
The posts_to_generate switch is optional and contains the number of posts to generate. This is useful if you want to only test a couple of posts for testing purposes.

You can also run all the steps at once:
```
curator --steps scrape summarize generate --posts_to_process 3 --client openai
```
A shorthand for running all the steps at once is:
```
curator --all --posts_to_process 3 --client openai
```

You can use additional flags to customize the steps. For example, you can use the --data_folder flag to specify the data folder.
```
curator --all --data_folder ./data --posts_to_process 3 --client openai
```

You can also use the --model flag to specify the model to use.
```
curator --all --model gpt-4o --posts_to_process 3 --client openai
```

You can also use the --log-level flag to specify the log level.
```
curator --all --log-level DEBUG --posts_to_process 3 --client openai
``` 

You can always list the instructions for the steps by using the --help flag.
```
curator --help
```

The configuration is stored in the etc/config.json file. You can edit the configuration file to customize the steps.
1. The list of substacks that you want to scrape can be modified in the scrapers/substack list.
2. The categories can be modified in the categories list.
3. The user prompt can be changed to improve the way the posts are summarized. Make sure that the whole prompt is valid JSON, meaning that you 
    - must keep it as a single line string
    - you must include the {{ post.md }} placeholder in the prompt.
    - you must include the {{ categories|join(', ') }} placeholder in the prompt.
    - you must instruct the prompt to return a valid JSON object, including 'summary', 'category', and an optional 'error' if the task cannot be completed.

The resulting summary will be stored in the data/summaries/summary_template.html file.

# Developer Documentation

## Running the container with Docker

Run the container with Docker:
```
docker run -it \
    -e OPENAI_API_KEY='your-api-key-here' \
    -v $(pwd)/data:/app/data \
    -v $(pwd):/app \
    --network host \
    curator
```

** Manual Install Chrome for Selenium Webdirver

Make sure that you have Chrome installed on your machine.

Main Chrome site: https://sites.google.com/chromium.org/driver/?pli=1
Download MacOs drivers: 
```
mkdir -p chromedriver
cd chromedriver
curl -O https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.58/mac-arm64/chromedriver-mac-arm64.zip
curl -O https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-arm64/chromedriver-mac-arm64.zip
unzip chromedriver-mac-arm64.zip
```

Install OpenSSL dependencies:
```
brew install openssl@1.1
```

Build the Docker image:
```
docker build --platform linux/arm64 -t curator .
or 
docker build --platform linux/amd64 -t curator .
```

Running it:
```
docker run --platform linux/amd64 -it \
    --env-file .env \
    -v ~/Code/curator/data:/app/data \
    -v ~/Code/curator/etc:/app/etc \
    --network host \
    curator python main.py --posts_to_process 2 --client openai
```

Don't forget to set the environment variables before running the scraper.
SUBSTACK_EMAIL="your_email@example.com"
SUBSTACK_PASSWORD="your_password"
OPENAI_API_KEY="your_openai_api_key"

** Set Environment Variables
Before running the scraper, set the necessary environment variables. Here are some examples:

For Bash:
```
export SUBSTACK_EMAIL="your_email@example.com"
export SUBSTACK_PASSWORD="your_password"
export OPENAI_API_KEY="your_openai_api_key"
```

For Windows:
```
set SUBSTACK_EMAIL="your_email@example.com"
set SUBSTACK_PASSWORD="your_password"
set OPENAI_API_KEY="your_openai_api_key"
```


** Create Environment and Install Dependencies
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Execute the script with the following command:
```
python main.py
```

You can execute only selected steps by using the --steps flag.
```
python main.py --steps scrape
python main.py --steps summarize
python main.py --steps generate
```
or multiple steps at once:
```
python main.py --steps summarize generate
```
The default data folder is ./data. You can change this by using the --data_folder flag.
```
python main.py --data_folder ./another_folder
``` 
By default, the script will scrape 5 posts and summarize 5 posts. You can change this by using the --posts_to_scrape and --posts_to_summarize flags.
```
python main.py --posts_to_scrape 10 --posts_to_summarize 10
``` 

