from django.core.mail import send_mail
from django.urls import reverse
import os 

def send_email_notification(subject, body, recipients, from_email="no-reply@example.com", fail_silently=False):
    """
    Sends an email notification using Django's send_mail utility.

    :param subject: Subject of the email
    :param body: Body/content of the email
    :param recipients: List of recipient email addresses
    :param from_email: Sender's email address
    :param fail_silently: If True, suppresses errors; otherwise raises exceptions
    """
    if not recipients:
        return  # No recipients, skip sending
    send_mail(
        subject,
        body,
        from_email,
        recipients,
        fail_silently=fail_silently
    )


from twilio.rest import Client

def send_sms_notification(client, body, phone_numbers, from_number="+1234567890"):
    """
    Sends SMS notifications via Twilio.

    :param client: An instance of twilio.rest.Client
    :param body: Text message content
    :param phone_numbers: List of recipient phone numbers (strings)
    :param from_number: Your Twilio phone number (or valid sending number)
    """
    if not phone_numbers:
        return
    for to_number in phone_numbers:
        client.messages.create(
            body=body,
            from_=from_number,
            to=to_number  # e.g., "+911234567890"
        )   

def send_whatsapp_notification(client, content_sid, content_variables, phone_numbers, from_whatsapp="whatsapp:+14155238886"):
    """
    Sends WhatsApp notifications via Twilio.

    :param client: An instance of twilio.rest.Client
    :param content_sid: Twilio content SID for pre-approved WhatsApp templates
    :param content_variables: JSON string of variables to fill in template
    :param phone_numbers: List of recipient WhatsApp phone numbers, e.g. ["whatsapp:+91XXXXXXXXXX"]
    :param from_whatsapp: Your Twilio WhatsApp sender number
    """
    if not phone_numbers:
        return
    for receiver in phone_numbers:
        client.messages.create(
            from_=from_whatsapp,
            content_sid=content_sid,
            content_variables=content_variables,
            to=receiver
        )


def send_call_notification(client, call_url, phone_numbers, from_number="+1234567890"):
    """
    Initiates voice calls via Twilio.

    :param client: An instance of twilio.rest.Client
    :param call_url: The URL containing TwiML instructions or a Twilio bin URL
    :param phone_numbers: List of phone numbers to call (e.g., ["+911234567890"])
    :param from_number: Your Twilio phone number
    """
    if not phone_numbers:
        return
    for receiver in phone_numbers:
        client.calls.create(
            from_=from_number,
            to=receiver,
            url=call_url
        )

def send_all_notifs(phone, email, incident_id, incident_type):
    """
    NEED TO IMPLEMENT THIS!!!
    """
    pass
    # url = reverse('resolve', args=[incident_id])
    # main_text = f"Dear Surakshak,\n\nPlease check out the incident snippet and other information at {url} to resolve the alert as soon as possible.  \n\nRegards, \nInstitution"
    # subject = f"Alert! Incident Type: {incident_type} Detected at {incident_type}"

    # account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    # auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    # twilio_client = Client(account_sid, auth_token)
    # send_sms_notification(
    #     client=twilio_client,
    #     body=main_text,
    #     from_number="+12317666829",
    #     phone_number=[phone]
    # )
    
    # send_call_notification(
    #     client=twilio_client,

    # )