# LinkedIn Email Personalization Tool

A Python script that uses the free Groq API to automatically generate personalized outreach emails for LinkedIn profiles, using AI to analyze each profile and create genuine, tailored messages.

## Features

✓ **Free LLM API**: Uses Groq's free tier (no credit card required)  
✓ **Intelligent Personalization**: Analyzes LinkedIn profiles to generate genuine praise  
✓ **Automatic Company Requirements Extraction**: Identifies business needs from profiles  
✓ **Batch Processing**: Generate emails for hundreds of contacts  
✓ **Professional Output**: Clean, formatted text file with all personalized emails  

## Prerequisites

- Python 3.7+
- Free Groq API key (get from https://console.groq.com/keys)

## Installation

### 1. Install Dependencies

```bash
pip install groq
```

### 2. Get a Free Groq API Key

1. Visit https://console.groq.com/keys
2. Sign up for a free account (no credit card required)
3. Generate an API key
4. Copy your API key

### 3. Set Environment Variable

**On macOS/Linux:**
```bash
export GROQ_API_KEY='your-api-key-here'
```

**On Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=your-api-key-here
```

**On Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY='your-api-key-here'
```

## Usage

### Step 1: Prepare Your LinkedIn Data

Create a JSON file with your LinkedIn profiles. Use the format from `linkedin_profiles_sample.json`:

```json
[
    {
        "name": "John Doe",
        "headline": "Marketing Manager at XYZ Corp",
        "about": "Passionate about branding and digital marketing...",
        "company": "XYZ Corp",
        "profile_url": "https://linkedin.com/in/johndoe"
    }
]
```

**Required fields:**
- `name`: Contact's full name
- `headline`: Their LinkedIn headline/title
- `about`: Their about/bio section
- `company`: Company name
- `profile_url`: LinkedIn profile URL (optional but helpful for tracking)

### Step 2: Run the Script

```bash
python linkedin_email_generator.py linkedin_profiles.json
```

Or use the default filename:
```bash
python linkedin_email_generator.py
```
(looks for `linkedin_profiles.json` in current directory)

### Step 3: Check Output

The script generates `personalized_emails.txt` with all personalized emails ready to send.

## Example Output

```
================================================================================
EMAIL #1
Recipient: Sarah Johnson
Company: Emirates Trading Company
================================================================================

Dear Sarah Johnson,

I hope you're doing well.

Your work in brand development and digital transformation is truly impressive, 
and I've noticed your focus on innovative customer engagement strategies.

I'm reaching out from Stream Advertising. Since 1999, we support clients across 
the UAE with branding, events and production solutions including signage, 
wayfinding, office and retail branding, exhibition stands, Fitouts, kiosks, 
custom fabrication, and large-format printing. Since we do our production 
in-house, we have complete quality control and have zero delays in deadlines. 
We always strive to go beyond client expectations.

With Emirates Trading Company expanding their brand presence across the region, 
I thought it would be worthwhile to see if there could be any upcoming 
opportunities where we might support your team as a reliable production partner.

I have attached our company profile. Please feel free to look through it. 
Look forward to hearing from you.

Have a wonderful week!
```

## How It Works

1. **Loads Profiles**: Reads LinkedIn profiles from your JSON file
2. **AI Analysis**: For each profile, sends it to the Groq API with a prompt to:
   - Generate a genuine, personalized compliment based on their background
   - Identify business needs/growth areas from their company and role
3. **Email Generation**: Fills in the email template with personalized content
4. **Saves Output**: Writes all personalized emails to a text file for easy copy-paste

## Free Groq API Limits

- **Rate Limit**: ~30 requests per minute on free tier
- **Model**: Uses Mixtral-8x7b (excellent quality, open source)
- **Cost**: Completely free
- **No Credit Card**: Required to get started

For bulk sending (100+ profiles), you may need to add a small delay between requests:

```python
import time
# Add this in the main loop
time.sleep(2)  # Wait 2 seconds between API calls
```

## Troubleshooting

### "GROQ_API_KEY environment variable not set"
- Make sure you've set the environment variable correctly
- Test it with: `echo $GROQ_API_KEY` (macOS/Linux) or `echo %GROQ_API_KEY%` (Windows)

### "File not found"
- Make sure your JSON file is in the same directory as the script
- Or provide the full path: `python linkedin_email_generator.py /path/to/profiles.json`

### "Invalid JSON"
- Validate your JSON file at https://jsonlint.com/
- Make sure all field names are quoted and properly formatted

### API Rate Limit
- The free tier allows ~30 requests per minute
- For large batches, add a 2-3 second delay between profiles
- Edit the script to add: `time.sleep(2)` in the main loop

## Customization

You can customize the email template by editing the `EMAIL_TEMPLATE` variable in the script:

```python
EMAIL_TEMPLATE = """Dear <name>,
...
```

**Available placeholders:**
- `<name>`: Contact's name
- `<praise>`: AI-generated personalized compliment
- `<company_name>`: Their company name
- `<requirement>`: AI-identified business need

## Tips for Best Results

1. **Rich Profiles**: The more detailed the LinkedIn profile (headline, about, etc.), the better the personalization
2. **Verify Output**: Always review generated emails before sending
3. **Test First**: Start with 5-10 profiles to see quality before running full batch
4. **Edit if Needed**: Feel free to manually edit generated emails in the output file
5. **Professional Tone**: The script aims for genuine, non-salesy messages

## Advanced Usage

### Filtering Profiles
Add logic to filter profiles before processing:
```python
# Only process marketing directors
profiles = [p for p in profiles if "marketing" in p.get("headline", "").lower()]
```

### Custom Prompts
Modify the `analysis_prompt` in `generate_personalization()` to change how the AI analyzes profiles.

### Different Email Template
Create multiple templates and use different ones for different profile types.

## Privacy & Data

- Your LinkedIn data stays local on your computer
- Only profile text is sent to Groq API for analysis
- No data is stored by the script or Groq beyond the API request

## Support

- Check Groq documentation: https://console.groq.com/docs
- LinkedIn data format issues? Verify JSON with: https://jsonlint.com/

## License

Free to use and modify for your outreach needs.

---

**Happy prospecting!** 🚀