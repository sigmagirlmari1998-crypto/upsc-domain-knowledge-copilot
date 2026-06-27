import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
api_key=os.getenv("GEMINI_API_KEY")
)

def ask_gemini(prompt):


    retries = 5

    for attempt in range(retries):

        try:

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text

        except Exception as e:

            error_msg = str(e)

        print(
            f"Gemini Error (Attempt {attempt + 1}): {error_msg}"
        )

        if (
            "503" in error_msg
            or "UNAVAILABLE" in error_msg
            or "RESOURCE_EXHAUSTED" in error_msg
        ):

            if attempt < retries - 1:

                wait_time = 2 * (attempt + 1)

                print(
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue

        return f"Error generating answer: {error_msg}"

    return "Gemini service unavailable after multiple retries."
