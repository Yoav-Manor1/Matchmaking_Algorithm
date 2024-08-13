import openai
from openai import OpenAI
import gspread
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI

# README and documentation
#
#    Explanation about Mentor and Mentee matching
# 1. Check out this Google spreadsheet for explanations about the formula for matching mentors and mentees:
#    https://docs.google.com/spreadsheets/d/1r3IXMAJ3RrnJlAERPdL31gCTKVuT4tgWEicKijL0tAw/edit?usp=sharing
# 2. This formula is represented in the prompt to GPT. If you wish to change the formula, you would also have to change
#    the prompt.
# 3. Right now, this script will generate a maximum of 10 matches per mentor, but this can also be changed by changing
#    the prompt.
#
#    How to copy the results to a spreadsheet
# 1. In order to copy the results to another spreadsheet, copy them from the pycharm output window into a new Google
#    spreadsheet, then, click on Data -> Split text to columns -> For separator choose Semicolon
#
#    How to set up the environment
# 1. Install Python. Go to https://www.python.org/downloads/ and install
# 2. PyCharm: Go to https://www.jetbrains.com/pycharm/download/ and install PyCharm community addition (free)
# 3. Create a new project in PyCharm. Take this file (main.py), and select all. Copy the entire content of this file
#    into the main.py inside the newly created project.
# 4. Copy the other attached file, service_account.json to the newly create project by copying and pasting into the
#    project's directory.
# 5. You will also need to replace the path to this file with the path on your computer:
SERVICE_ACCOUNT_FILE_PATH = '/Users/name/Project/pythonProject/Secret Key/'  # <-- Change the actual path to the file
SERVICE_ACCOUNT_FILE = SERVICE_ACCOUNT_FILE_PATH + 'service_account.json'
# 6. From your project's command line in PyCharm, pip install the following packages:
#    google-auth
#    google-auth-oauthlib
#    google-auth-httplib2
#    google-api-python-client
#    openai
#    gspread
# 7. Make sure you are using the correct Google spreadsheet. The script is using this spreadsheet:
#    Link to your spreadsheet questionnaire answers. If you would
#    like to use a different spreadsheet, please replace the spreadsheet ID to the ID of the spreadsheet you would like
#    to use, and share the new spreadsheet file with the service account email address.
#    We will use the Sheet in read only mode
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
#    If we would like to access another spreadsheet, we would need to change the spreadsheet ID, and also to share the
#    new form with the service account email address. The service account email address is placed inside the
#    service_account.json file, and looks similar to this: accessgoogleapi@something.gserviceaccount.com
SPREADSHEET_ID = 'LAST_PART_OF_YOUR_SPREADSHEET_URL'
#    This is the name of the spreadsheet tab that we will access. If you would like to access a different tab, you will
#    need to change this as well.
RANGE_NAME = 'Form Responses'
#
#    Run the project by clicking the 'Play' button on the upper right side of the PyCharm window. Please wait about 20
#    seconds to see the first set of results (because getting results from GPT is slow).

# Sources: For Google sheet installations, I worked with this youtube video: https://www.youtube.com/watch?v=hyUw-koO2DA


# Spreadsheet columns definitions:
AFFILIATION_COL = 2
ROLE_COL = 3
FIRST_NAME_COL = 7
LAST_NAME_COL = 8
EMAIL_COL = 9
CITY_COL = 11
STATE_COL = 12
MEETING_LOCATION_COL = 17
MEETING_PREFERENCE_COL = 18
GENDER_COL = 14
GENDER_PREFERENCE_COL = 15
OCCUPATION_COL = 21
COMPANY_COL = 22
INDUSTRY_COL = 24
WORK_HISTORY_COL = 26
CAREER_PATH_COL = 27
EDUCATION_COL = 28
HIGHER_EDUCATION_COL = 29
DEGREE_COL = 30
VALUES_COL = 33
ABOUT_ME_COL = 34
HOBBIES_COL = 35
FOCUS_AREA_COL = 36
ANSWER_Q1_EXPECTATIONS_AND_HOPES_COL = 39
ANSWER_Q2_ANYTHING_ELSE_COL = 40

# Function to read from the google spreadsheet mentioned above
def access_spreadsheet():
    # Authenticate and create the Sheets API service, read only access
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API to get the values
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        return values


# A function to send input to GPT and get a response
def get_ai_response(prompt):
    try:
        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,  # Set the temperature to 0
            top_p=1  # Set top_p to 1 for more deterministic output
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {str(e)}"

# A function for filtering out mentees who do not match by gender preferences of either mentor or mentee
def is_gender_match(gender_mentor, gender_pref_mentor, gender_mentee, gender_pref_mentee):
    # Both are No preference
    if "No preference" in str(gender_pref_mentor) and "No preference" in str(gender_pref_mentee):
        return True

    # None are No preference
    if str(gender_mentor) == str(gender_pref_mentee) and str(gender_mentee) == str(gender_pref_mentor):
        return True

    # Mentor is No preference and Mentee has preference
    if "No preference" in str(gender_pref_mentor) and str(gender_mentor) == str(gender_pref_mentee):
        return True

    # Mentee is No preference and Mentor has preference
    if "No preference" in str(gender_pref_mentee) and str(gender_mentee) == str(gender_pref_mentor):
        return True

    return False

# Sometimes GPT adds empty lines to the output. This functions gets rid of them, so we can move the output into a csv easily.
def remove_empty_lines(input_string):
    # Split the input string into lines
    lines = input_string.split('\n')

    # Filter out empty lines
    non_empty_lines = [line for line in lines if line.strip()]

    # Join the non-empty lines back into a string
    result = '\n'.join(non_empty_lines)

    return result

# This is the initial prompt, we will then add the mentor and mentees to this prompt, and sent to GPT to get the matches
prompt = "Below are two sections. The first section contains details about a mentor. The second section contains a list " \
         "of possible mentees. Your job is to find the best 10 mentees for each mentor. You will do so by analyzing " \
         "some considerations, and then giving the match a score between 0 and 40. " \
         "overall score = 0 is no match, overall score = 40 is a perfect match." \
         "Considerations: \n" \
         "Location and in person vs. zoom meetings. For this score, you will need to use the 'city', 'state', " \
         "'meeting location preference' and 'meeting type' categories." \
         "If either mentor or mentee live no more than 30 miles away from each other, " \
         "please check if they are ok with meeting over video conferencing (zoom). " \
         "If they live more than 30 miles away and either of them don't wish to meet over zoom, " \
         "it disqualifies the match completely" \
         "For example, if the mentee lives in Los Angeles, California and the mentor lives in San Francisco, California, " \
         "which are over 30 miles away, then, we will look at their zoom preferences. If one of them would like only " \
         "to meet in person, then the match is disqualified completely. " \
         "Another example for location and in person vs. zoom meeting: " \
         "if the mentee lives in Palo Alto, California, and the mentor lives in Sunnyvale, California, then their " \
         "zoom preferences don't matter, because Palo Alto and Sunnyvale are located less than 30 miles away of each other, " \
         "and so the mentor and mentee can meet either in person or over zoom. " \
         "Another example, is if both mentor and mentee live at the same metropolitan area, such as the San " \
         "Francisco Bay Area, then they will be considered to be less than 30 miles away. " \
         "If this consideration is disqualified, the match will receive the overall score of 0. \n" \
         "Scoring: These considerations will each receive a numerical value between 0 and 10" \
         "1. Occupation and Work history similarity score (between 0 and 10) for this, you will need to look at the " \
         "'occupation', 'career path', 'Industry', as well as at the mentor's 'work history' to see if they match. " \
         "For example: if the mentee is an engineer, and the mentor was also an engineer in their current " \
         "or past roles, or an engineering leader, then the occupation will receive a score of 10/10. " \
         "Another example for occupation and work history score is: if the mentee is a marketing manager and the mentor is a sales executive, " \
         "the occupation and work history will receive a score of 6/10, because these occupations are somewhat adjacent. " \
         "Another example for occupation and work history is: if the mentee is a writer but the mentor is an accountant, " \
         "and they have never been writers in their past, then " \
         "the occupation will receive the score of 0/10, because these occupations and work histories are very different." \
         "Another example: if both mentor and mentee are from the same industry, the Occupation score will be high. " \
         "another example for Occupation similarity score is if the mentor used to work or is working in medical devices, and the mentee is in " \
         "software, then the Occupation similarity score will be medium, because both industries are in the technology " \
         "sector. " \
         "2. Education similarity:  (between 0 and 10). For this score, you will need to use the 'Education', " \
         "'Higher education' and 'degree' categories. " \
         "For example: If both mentee and mentor studied the same subjects, then the score will be high. " \
         "if the area of study is adjacent (such as communications and marketing), the score will be medium. " \
         "if the area of study is very different (such as archaeology and data science), then the score will be low. \n" \
         "3. Values score: (between 0 and 10) For this score, you will need to use the 'values', 'about me', " \
         "'focus area', 'Expectations and hopes' and 'hobbies'. " \
         "As much as possible, make sure the mentee's are similar or aligned to the mentor's. " \
         "In addition, for the value consideration, please also match the question that starts with " \
         "'Why do you want to participate in the Jewish Community Mentorship Program', in order to find more " \
         "matches and mismatches between mentee and mentor. \n" \
         "4. Anything else score: (between 0 and 10). For this score, you will need to consider the " \
         "'would you like to add anything else?', 'Occupation', 'Work history', 'Values', 'About me', 'Expectations and hopes', " \
         "'Meeting type preference', 'Affiliation' and 'Company' categories. This score purpose is to check for any additional mismatches between " \
         "the mentor and mentee." \
         "For example: If the mentee would like to be matched with a mentor that has experience as a business owner," \
         "but the mentor's work history and occupation don't suggest that they have experience as a business owner, then " \
         "the 'anything else' score will be 0/10. " \
         "Another example: If the mentee or the mentor wishes to be matched with a mentor or mentee who is religious, or orthodox, and the other person " \
         "didn't specify any religious affiliation, then the score will be 0/10. " \
         "Another example: If the mentee would like to be matched with someone who is involved within the Jewish community, " \
         "but the mentor didn't specify any connection to the Jewish community, then the score will be 0/10."

prompt += "When giving the scores for the mentorship compatibility, please only use the following calculation: \n" \
          "Don't ever list mentees with an overall score of 0, or with a 'no' at the yes/no considerations. " \
          "Use the exact following very strict format. Don't use any other formats other than the one listed below. " \
          "Format for a single mentee and mentor line: " \
          "[Mentor full name]; [Mentor email]; " \
          "[Mentee full name]; [Mentee email]; " \
          "[overall score] / 40; " \
          "Occupation [score] /10; " \
          "Education [score] / 10; " \
          "Values [score] / 10; " \
          "Anything else [score] / 10; " \
          "[rationale] " \
          "End of format. " \
          "There must only be one line per one mentor and one mentee. The output must be in the format above, " \
          "Please keep the rationale short, under 500 characters. " \
          "Please output the top 10 compatible mentees. " \
          "You can list less than 10, but not more than 10. " \
          "Don't put '*' in the output. Don't put '-' in the output. Do not output a bullet list or a numbered list. " \
          "A record should always start with the name of the mentor. " \
          "Please sort the mentees according to score, from high to lower"

# Initialize the client with your API key
client = OpenAI(api_key="XXX") #put in actual key

# Read the spreadsheet
response_spreadsheet = access_spreadsheet()

for j in range(1, len(response_spreadsheet)):
    # Get the next mentor
    mentor_counter = 0
    mentee_counter = 0
    if "Mentor" in str(response_spreadsheet[j][ROLE_COL]):
        current_record = "Here is the Mentor record: \n"
        mentor_counter += 1
        current_record += " First name: " + response_spreadsheet[j][FIRST_NAME_COL]
        current_record += "\n"
        current_record += " Last name: " + response_spreadsheet[j][LAST_NAME_COL]
        current_record += "\n"
        current_record += " email: " + response_spreadsheet[j][EMAIL_COL]
        current_record += "\n"
        current_record += " City: " + response_spreadsheet[j][CITY_COL]
        current_record += "\n"
        current_record += " State: " + response_spreadsheet[j][STATE_COL]
        current_record += "\n"
        current_record += " Meeting location preference: " + response_spreadsheet[j][MEETING_LOCATION_COL]
        current_record += "\n"
        current_record += " Meeting type preference: " + response_spreadsheet[j][MEETING_PREFERENCE_COL]
        current_record += "\n"
        current_record += " Gender: " + response_spreadsheet[j][GENDER_COL]
        current_record += "\n"
        current_record += " Gender preference: " + response_spreadsheet[j][GENDER_PREFERENCE_COL]
        current_record += "\n"
        current_record += " Occupation: " + response_spreadsheet[j][OCCUPATION_COL]
        current_record += "\n"
        current_record += " Affiliation: " + response_spreadsheet[j][AFFILIATION_COL]
        current_record += "\n"
        current_record += " Company: " + response_spreadsheet[j][COMPANY_COL]
        current_record += "\n"
        current_record += " Industry: " + response_spreadsheet[j][INDUSTRY_COL]
        current_record += "\n"
        current_record += " Work history: " + response_spreadsheet[j][WORK_HISTORY_COL]
        current_record += "\n"
        current_record += " Career path: " + response_spreadsheet[j][CAREER_PATH_COL]
        current_record += "\n"
        current_record += " Education: " + response_spreadsheet[j][EDUCATION_COL]
        current_record += "\n"
        current_record += " Higher education: " + response_spreadsheet[j][HIGHER_EDUCATION_COL]
        current_record += "\n"
        current_record += " Degree: " + response_spreadsheet[j][DEGREE_COL]
        current_record += "\n"
        current_record += " Values: " + response_spreadsheet[j][VALUES_COL]
        current_record += "\n"
        current_record += " About me: " + response_spreadsheet[j][ABOUT_ME_COL]
        current_record += "\n"
        current_record += " Hobbies: " + response_spreadsheet[j][HOBBIES_COL]
        current_record += "\n"
        current_record += " Focus area: " + response_spreadsheet[j][FOCUS_AREA_COL]
        current_record += "\n"
        current_record += " Expectations and hopes: " + response_spreadsheet[j][ANSWER_Q1_EXPECTATIONS_AND_HOPES_COL]
        current_record += "\n"
        current_record += " Would you like to add anything else? " + \
                          response_spreadsheet[j][ANSWER_Q2_ANYTHING_ELSE_COL]
        current_record += "\n"

        current_record += "And here is the list of Mentee records: \n"
        for i in range(1, len(response_spreadsheet)):

            # Add this record to the prompt only if this is a Mentee record, and there is a gender match.
            #
            if "Mentee" in str(response_spreadsheet[i][ROLE_COL]) and \
                    is_gender_match(response_spreadsheet[i][GENDER_COL],
                                    response_spreadsheet[i][GENDER_PREFERENCE_COL],
                                    response_spreadsheet[j][GENDER_COL],
                                    response_spreadsheet[j][GENDER_PREFERENCE_COL]):
                # Build the mentee record
                mentee_counter += 1
                current_record += " First name: " + response_spreadsheet[i][FIRST_NAME_COL]
                current_record += "\n"
                current_record += " Last name: " + response_spreadsheet[i][LAST_NAME_COL]
                current_record += "\n"
                current_record += " email: " + response_spreadsheet[i][EMAIL_COL]
                current_record += "\n"
                current_record += " City: " + response_spreadsheet[i][CITY_COL]
                current_record += "\n"
                current_record += " State: " + response_spreadsheet[i][STATE_COL]
                current_record += "\n"
                current_record += " Meeting location preference: " + response_spreadsheet[i][MEETING_LOCATION_COL]
                current_record += "\n"
                current_record += " Meeting type preference: " + response_spreadsheet[i][MEETING_PREFERENCE_COL]
                current_record += "\n"
                current_record += " Gender: " + response_spreadsheet[i][GENDER_COL]
                current_record += "\n"
                current_record += " Gender preference: " + response_spreadsheet[i][GENDER_PREFERENCE_COL]
                current_record += "\n"
                current_record += " Occupation: " + response_spreadsheet[i][OCCUPATION_COL]
                current_record += "\n"
                current_record += " Affiliation: " + response_spreadsheet[i][AFFILIATION_COL]
                current_record += "\n"
                current_record += " Company: " + response_spreadsheet[i][COMPANY_COL]
                current_record += "\n"
                current_record += " Industry: " + response_spreadsheet[i][INDUSTRY_COL]
                current_record += "\n"
                current_record += " Work history: " + response_spreadsheet[i][WORK_HISTORY_COL]
                current_record += "\n"
                current_record += " Career path: " + response_spreadsheet[i][CAREER_PATH_COL]
                current_record += "\n"
                current_record += " Education: " + response_spreadsheet[i][EDUCATION_COL]
                current_record += "\n"
                current_record += " Higher education: " + response_spreadsheet[i][HIGHER_EDUCATION_COL]
                current_record += "\n"
                current_record += " Degree: " + response_spreadsheet[i][DEGREE_COL]
                current_record += "\n"
                current_record += " Values: " + response_spreadsheet[i][VALUES_COL]
                current_record += "\n"
                current_record += " About me: " + response_spreadsheet[i][ABOUT_ME_COL]
                current_record += "\n"
                current_record += " Hobbies: " + response_spreadsheet[i][HOBBIES_COL]
                current_record += "\n"
                current_record += " Focus area: " + response_spreadsheet[i][FOCUS_AREA_COL]
                current_record += "\n"
                current_record += " Expectations and hopes: " + \
                                  response_spreadsheet[i][ANSWER_Q1_EXPECTATIONS_AND_HOPES_COL]
                current_record += "\n"
                current_record += " Would you like to add anything else? " + \
                                  response_spreadsheet[i][ANSWER_Q2_ANYTHING_ELSE_COL]
                current_record += "\n"

        # Print for debugging
        # print(prompt + current_record)
        # print("Current Mentor: " + response_spreadsheet[j][FIRST_NAME_COL])
        # print("Number of Mentors: " + str(mentor_counter))
        # print("Number of Mentees: " + str(mentee_counter))
        # print("Total records: " + str(mentee_counter + mentor_counter))
        # print("Length of prompt [chars]: " + str(len(prompt + current_record)))
        # print("Number of words in prompt: " + str(len(prompt.split()) + len(current_record.split())))
        # print("Number of OAI tokens in prompt (by chars): " + str(len(prompt+current_record)/4))
        # print("Number of OAI tokens in prompt (by word): " + str(len(prompt.split()) + len(current_record.split()) / 1.3))
        openai_matching = get_ai_response(prompt + current_record)
        csv_output = remove_empty_lines(openai_matching)
        print(csv_output)

