# A simple script to quickly test if the chatbot is fully working, mostly regarding the complex authentication requirements.
# This allows to skip the streamlit interface and get a faster feedback loop.
import chatbot

chatbot.generate_ai_answer(
    "Give me a short resume of what is Glance in OpenStack, based on the provided context ?")
