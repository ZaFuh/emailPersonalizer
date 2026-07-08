#!/usr/bin/env python3
"""
LinkedIn Profile Email Personalizer
Uses Groq API (free) to generate personalized outreach emails for LinkedIn profiles.
"""

import json
import sys
import csv
from datetime import datetime
import os
from urllib.parse import urlparse

try:
    from groq import Groq
except ImportError:
    print("Error: groq library not installed.")
    print("Install it with: pip install groq")
    sys.exit(1)


# Email template
EMAIL_TEMPLATE = """Dear <name>,

I hope you're doing well.

<praise>

I'm reaching out from Stream Advertising. Since 1999, we support clients across the UAE with branding, events and production solutions including signage, wayfinding, office and retail branding, exhibition stands, Fitouts, kiosks, custom fabrication, and large-format printing. Since we do our production in-house, we have complete quality control and have zero delays in deadlines. We always strive to go beyond client expectations.

With <company_name> <requirement>, I thought it would be worthwhile to see if there could be any upcoming opportunities where we might support your team as a reliable production partner.

I have attached our company profile. Please feel free to look through it. Look forward to hearing from you.

Have a wonderful week!"""


def load_linkedin_profiles(file_path):
    """
    Load LinkedIn profiles from a CSV file.
    Expected format (column names):
    - Lead Name (or Name)
    - Company Name (or Company)
    - Linkedin (or LinkedIn URL)
    
    Other columns are ignored.
    """
    try:
        profiles = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if reader.fieldnames is None:
                print(f"Error: CSV file '{file_path}' is empty.")
                sys.exit(1)
            
            # Find the correct column names (case-insensitive)
            fieldnames = {field.lower(): field for field in reader.fieldnames}
            
            # Identify column names
            name_col = None
            company_col = None
            linkedin_col = None
            
            for key in fieldnames:
                if 'name' in key and 'lead' in key:
                    name_col = fieldnames[key]
                elif 'name' in key and name_col is None:
                    name_col = fieldnames[key]
                elif 'company' in key:
                    company_col = fieldnames[key]
                elif 'linkedin' in key:
                    linkedin_col = fieldnames[key]
            
            if not name_col:
                print("Error: CSV must have a 'Lead Name' or 'Name' column.")
                sys.exit(1)
            if not company_col:
                print("Error: CSV must have a 'Company Name' or 'Company' column.")
                sys.exit(1)
            if not linkedin_col:
                print("Error: CSV must have a 'Linkedin' or 'LinkedIn' column.")
                sys.exit(1)
            
            for row in reader:
                name = row[name_col].strip()
                company = row[company_col].strip()
                linkedin_url = row[linkedin_col].strip()
                
                # Skip empty rows
                if not name or not company:
                    continue
                
                profile = {
                    "name": name,
                    "company": company,
                    "profile_url": linkedin_url,
                    "headline": f"Professional at {company}",
                    "about": f"Connected on LinkedIn at {linkedin_url}"
                }
                profiles.append(profile)
        
        return profiles
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file '{file_path}': {str(e)}")
        sys.exit(1)


def generate_personalization(client, profile):
    """
    Use Groq API to generate personalized praise and identify company requirements.
    """
    name = profile.get("name", "there")
    headline = profile.get("headline", "")
    about = profile.get("about", "")
    company = profile.get("company", "their company")
    
    # Create a prompt for the LLM to analyze the profile
    analysis_prompt = f"""Analyze this LinkedIn profile and provide:
1. A genuine, personalized compliment (1-2 sentences) about their professional achievements or expertise
2. A brief observation about the company's likely marketing/branding needs (1-2 sentences)

Profile:
Name: {name}
Headline: {headline}
About: {about}
Company: {company}

Format your response as JSON with keys: "praise" and "requirement"
Both values should be plain text, not including the variable names."""

    try:
        message = client.messages.create(
            model="mixtral-8x7b-32768",  # Free model available on Groq
            max_tokens=300,
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        # Try to parse as JSON
        try:
            # Find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "praise": f"I've been impressed by your work in {headline.lower()}.",
                "requirement": f"With {company}'s growth in the market"
            }
        
        return result
        
    except Exception as e:
        print(f"Error calling Groq API for {name}: {str(e)}")
        return {
            "praise": f"I've been impressed by your professional background.",
            "requirement": f"With {company}'s business needs"
        }


def personalize_email(template, profile, personalization):
    """
    Replace placeholders in the email template with personalized content.
    """
    email = template.replace("<name>", profile.get("name", "there"))
    email = email.replace("<praise>", personalization.get("praise", ""))
    email = email.replace("<company_name>", profile.get("company", "your company"))
    email = email.replace("<requirement>", personalization.get("requirement", ""))
    
    return email


def main():
    """Main function to orchestrate the email generation process."""
    
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not set.")
        print("Get a free API key from https://console.groq.com/keys")
        print("Then set it with: export GROQ_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Initialize Groq client
    client = Groq(api_key=api_key)
    
    # Get input file path from command line or use default
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "linkedin_profiles.csv"
    
    print(f"Loading LinkedIn profiles from '{input_file}'...")
    profiles = load_linkedin_profiles(input_file)
    print(f"Found {len(profiles)} profiles.\n")
    
    # Generate personalized emails
    emails = []
    
    for i, profile in enumerate(profiles, 1):
        name = profile.get("name", "Unknown")
        print(f"[{i}/{len(profiles)}] Personalizing email for {name}...", end=" ")
        
        # Generate personalization using LLM
        personalization = generate_personalization(client, profile)
        
        # Create personalized email
        email = personalize_email(EMAIL_TEMPLATE, profile, personalization)
        
        # Store email with metadata
        emails.append({
            "name": name,
            "company": profile.get("company", "Unknown"),
            "email": email
        })
        
        print("✓")
    
    # Write output file
    output_file = "personalized_emails.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PERSONALIZED EMAIL OUTREACH\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total emails: {len(emails)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, email_data in enumerate(emails, 1):
            f.write(f"\n{'='*80}\n")
            f.write(f"EMAIL #{i}\n")
            f.write(f"Recipient: {email_data['name']}\n")
            f.write(f"Company: {email_data['company']}\n")
            f.write(f"{'='*80}\n\n")
            f.write(email_data['email'])
            f.write("\n\n")
    
    print(f"\n✓ Successfully generated {len(emails)} personalized emails!")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()