from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevOps Agentic Network"
    GITHUB_TOKEN: str = "mock_github_token"
    # Yeni eklenen alanlar:
    GITHUB_OWNER: str = "mock_owner"
    GITHUB_REPO: str = "mock_repo"
    
    JIRA_API_TOKEN: str = "mock_jira_token"
    JIRA_DOMAIN: str = "https://mock.atlassian.net"
    JIRA_USER_EMAIL: str = "mock@example.com"
    LLM_API_KEY: str = "mock_key"

    class Config:
        env_file = ".env"

settings = Settings()