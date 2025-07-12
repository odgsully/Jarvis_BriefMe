#!/usr/bin/env python3
"""Debug script to find Google Sheets GIDs and inspect worksheet content."""

import asyncio
import httpx

DOCUMENT_ID = "1pMNR5i3v1T-N63QnR_03X7ARWRR9PWJ3j0NP_jd4d7M"

async def test_gid(gid: str):
    """Test a specific GID and show the headers and first few rows."""
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/export?format=csv&gid={gid}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(csv_url, follow_redirects=True)
            
            if response.status_code == 200 and response.text.strip():
                lines = response.text.strip().split('\n')
                headers = lines[0] if lines else "No headers"
                row_count = len(lines) - 1  # Exclude header row
                
                print(f"GID {gid}: SUCCESS")
                print(f"  Headers: {headers}")
                print(f"  Row count: {row_count}")
                
                # Show first 2 data rows if available
                if len(lines) > 1:
                    for i, line in enumerate(lines[1:3], 1):
                        print(f"  Row {i}: {line[:100]}..." if len(line) > 100 else f"  Row {i}: {line}")
                
                print()
                return True
            else:
                print(f"GID {gid}: Failed - Status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"GID {gid}: Error - {e}")
        return False

async def main():
    """Test different GIDs to find the correct worksheets."""
    print(f"Testing Google Sheets document: {DOCUMENT_ID}")
    print("=" * 60)
    
    # Test GIDs 0-10 first
    print("Testing standard GIDs (0-10):")
    for gid in range(11):
        await test_gid(str(gid))
    
    # Test some common higher GID values
    print("\nTesting common higher GIDs:")
    common_gids = ["100", "200", "500", "1000", "2000", 
                   "123456789", "987654321", "111111111", 
                   "1234567890", "2147483647"]
    for gid in common_gids:
        await test_gid(gid)
    
    print("\nBased on the headers above, identify which GID corresponds to:")
    print("1. 'Transcript_Summaries' - should have Date, URL, Title columns")
    print("2. 'cs_terms' - should have Term, Definition columns") 
    print("3. 'espanol' - should have English, Spanish columns")
    print("\nWorkbook: jarvis notion python")

if __name__ == "__main__":
    asyncio.run(main())