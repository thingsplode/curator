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

