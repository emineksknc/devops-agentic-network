from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevOps Agentic Network"
    GITHUB_TOKEN: str = "mock_github_token"
    GITHUB_OWNER: str = "mock_owner"
    GITHUB_REPO: str = "mock_repo"
    
    JIRA_API_TOKEN: str = "mock_jira_token"
    JIRA_DOMAIN: str = "https://mock.atlassian.net"
    JIRA_USER_EMAIL: str = "mock@example.com"
    JIRA_PROJECT_KEY: str = "mock_project_key"
    LLM_API_KEY: str = "mock_key"
    
    # 🎯 EKSİK OLAN ALAN BURASIYDI: Pydantic'e bu alanı tanıtıyoruz
    LLM_MODEL: str = "llama3"
    LLM_PROVIDER: str = "ollama"
    OLLAMA_HOST: str = "http://localhost:11434"

    DAN_DB_PATH: str = "data/dan.db"

    # LangFuse gozlemlenebilirlik (bos birakilirsa tracing no-op olur)
    LANGFUSE_SECRET_KEY: str = "mock_langfuse_secret"
    LANGFUSE_PUBLIC_KEY: str = "mock_langfuse_public"
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"
        # Eğer .env içinde başka ekstra alanlar da olursa çökmesin diye:
        extra = "allow" 

settings = Settings()