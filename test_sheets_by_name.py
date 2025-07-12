#!/usr/bin/env python3
"""Test accessing Google Sheets by sheet name in the URL."""

import asyncio
import httpx
import urllib.parse

DOCUMENT_ID = "1pMNR5i3v1T-N63QnR_03X7ARWRR9PWJ3j0NP_jd4d7M"

async def test_sheet_by_name(sheet_name: str):
    """Test accessing a sheet by name."""
    try:
        # URL encode the sheet name
        encoded_name = urllib.parse.quote(sheet_name)
        
        # Try different URL formats
        urls = [
            f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/gviz/tq?tqx=out:csv&sheet={encoded_name}",
            f"https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/export?format=csv&sheet={encoded_name}",
        ]
        
        for url in urls:
            print(f"\nTesting sheet '{sheet_name}' with URL format:")
            print(f"  {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                
                if response.status_code == 200 and response.text.strip():
                    lines = response.text.strip().split('\n')
                    print(f"  SUCCESS!")
                    print(f"  Headers: {lines[0] if lines else 'No headers'}")
                    print(f"  Row count: {len(lines) - 1}")
                    if len(lines) > 1:
                        print(f"  First data row: {lines[1][:100]}..." if len(lines[1]) > 100 else f"  First data row: {lines[1]}")
                    return True
                else:
                    print(f"  Failed - Status {response.status_code}")
                    
    except Exception as e:
        print(f"  Error: {e}")
    
    return False

async def main():
    """Test different sheet names."""
    print("Testing Google Sheets document by sheet name")
    print("=" * 60)
    
    sheet_names = [
        "espanol",
        "cs_terms", 
        "Transcript_Summaries",
        "Sheet1",
        "Sheet2", 
        "Sheet3"
    ]
    
    for sheet_name in sheet_names:
        await test_sheet_by_name(sheet_name)
    
    print("\n" + "=" * 60)
    print("If only 'espanol' works, the other sheets may not exist in the Google Sheets document yet.")
    print("Check that Zapier has synced all three Notion databases to Google Sheets.")

if __name__ == "__main__":
    asyncio.run(main())