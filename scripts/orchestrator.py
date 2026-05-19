# /Users/zhaowenlong/workspace/dev.self-wiki/scripts/orchestrator.py
import os
from pathlib import Path


class SelfWikiOrchestrator:
    def __init__(self, workspace_root):
        self.root = Path(workspace_root)
        self.wiki_dir = self.root / "wiki"
        self.audit_file = self.root / "outputs/audit.md"
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
    workspace_root = "/Users/zhaowenlong/workspace/dev.self-wiki"
    orchestrator = SelfWikiOrchestrator(workspace_root)
    print(orchestrator.generate_audit_prompt())
