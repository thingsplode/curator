** Install Chrome for Selenium Webdirver

Make sure that you have Chrome installed on your machine.

Main Chrome site: https://sites.google.com/chromium.org/driver/?pli=1
Download MacOs drivers: 
```
mkdir -p chromedriver
cd chromedriver
curl -O https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.58/mac-arm64/chromedriver-mac-arm64.zip
unzip chromedriver-mac-arm64.zip
```

Install OpenSSL dependencies:
```
brew install openssl@1.1
```

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

