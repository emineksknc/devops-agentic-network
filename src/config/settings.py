from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevOps Agentic Network"
    GITHUB_TOKEN: str = "mock_github_token"
    JIRA_API_TOKEN: str = "mock_jira_token"
    JIRA_DOMAIN: str = "https://mock.atlassian.net"
    LLM_API_KEY: str = "mock_key"

    class Config:
        env_file = ".env"

settings = Settings()