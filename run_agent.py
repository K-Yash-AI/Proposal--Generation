#!/usr/bin/env python3
"""
Simple CLI to run the Proposal Agent.
"""
import sys
from agents.proposal_agent import ProposalAgent
from utils.logger import log


def main():
    """Run the proposal agent with CLI inputs."""
    print("\n" + "="*60)
    print("Welcome to the Proposal Generation Agent")
    print("="*60 + "\n")
    
    # Get required client information
    try:
        client_name = input("Client Name (required): ").strip()
        if not client_name:
            print("Error: Client name is required")
            sys.exit(1)
        
        client_company = input("Client Company (optional, press Enter to skip): ").strip() or None
        client_email = input("Client Email (optional, press Enter to skip): ").strip() or None
        prepared_by = input("Prepared By (optional, press Enter to use default): ").strip() or None
        
        transcripts_limit = input("Number of transcripts to fetch (default 5): ").strip()
        if transcripts_limit:
            try:
                transcripts_limit = int(transcripts_limit)
            except ValueError:
                print("Invalid number, using default (5)")
                transcripts_limit = 5
        else:
            transcripts_limit = 5
        
        upload_choice = input("Upload to Google Drive? (y/n, default: n): ").strip().lower()
        upload_to_drive = upload_choice in ["y", "yes"]
        
        print("\n" + "="*60)
        print("Generating proposal...")
        print("="*60 + "\n")
        
        # Create and run the agent
        agent = ProposalAgent()
        result = agent.run(
            client_name=client_name,
            client_company=client_company,
            client_email=client_email,
            prepared_by=prepared_by,
            transcripts_limit=transcripts_limit,
            use_fixed_format=True,
            upload_to_drive=upload_to_drive,
        )
        
        print("\n" + "="*60)
        log.info(f"[success]✓ Proposal saved to: {result['local_path']}[/success]")
        
        if "drive_link" in result and result["drive_link"]:
            print(f"\n[bold blue]📎 Shareable Link:[/bold blue]")
            print(f"{result['drive_link']}")
        
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nAgent interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

