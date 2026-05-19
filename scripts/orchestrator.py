import os
from pathlib import Path


def load_env(env_path):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Load .env
load_env(Path(__file__).parent.parent / ".env")
WORKSPACE_ROOT = Path(
    os.environ.get(
        "WORKSPACE_PATH", "/Users/zhaowenlong/workspace/dev.self-wiki/self-wiki"
    )
).parent


class SelfWikiOrchestrator:
    def __init__(self, workspace_root):
        self.root = Path(workspace_root)
        self.wiki_dir = self.root / "self-wiki/wiki"
        self.audit_file = self.root / "self-wiki/outputs/audit.md"
        self.gemini_config = self.root / "GEMINI.md"

    def generate_audit_prompt(self):
        """Generates the automated prompt for the AI to perform the linting."""
        with open(self.gemini_config, "r") as f:
            instructions = f.read()

        prompt = f"""
        Act as the Self-Wiki Architect. Using the following Operating Manual:
        {instructions}

        Perform a comprehensive audit of the files in {self.wiki_dir}.
        Focus specifically on finding 'Red Links' and 'Cognitive Shifts' (contradictions that show growth).
        Output the results directly into the format required for {self.audit_file}.
        """
        return prompt

    def run_sync(self):
        # Logic to trigger AI sync via CLI or API
        print("Triggering Smart Merge for new raw entries...")


if __name__ == "__main__":
    # Example usage
    orchestrator = SelfWikiOrchestrator(WORKSPACE_ROOT)
    print(orchestrator.generate_audit_prompt())
