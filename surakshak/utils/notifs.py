from django.core.mail import send_mail
from django.urls import reverse
from twilio.rest import Client
import os


def send_email_notification(
    subject, body, recipients, from_email="no-reply@example.com", fail_silently=False
):
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
    send_mail(subject, body, from_email, recipients, fail_silently=fail_silently)


def send_sms_notification(client, body, phone_numbers, from_number="+1234567890"):
    """
    Sends SMS notifications via Twilio.

    :param client: An instance of twilio.rest.Client
    :param body: Text message content
    :param phone_numbers: List of recipient phone numbers (strings)
    :param from_number: Your Twilio phone number (or valid sending number)
    """
    for to_number in phone_numbers:
        client.messages.create(
            body=body, from_=from_number, to=to_number  # e.g., "+911234567890"
        )


def send_whatsapp_notification(
    client,
    content_sid,
    content_variables,
    phone_numbers,
    from_whatsapp="whatsapp:+14155238886",
):
    """
    Sends WhatsApp notifications via Twilio.

    :param client: An instance of twilio.rest.Client
    :param content_sid: Twilio content SID for pre-approved WhatsApp templates
    :param content_variables: JSON string of variables to fill in template
    :param phone_numbers: List of recipient WhatsApp phone numbers, e.g. ["whatsapp:+91XXXXXXXXXX"]
    :param from_whatsapp: Your Twilio WhatsApp sender number
    """
    for receiver in phone_numbers:
        client.messages.create(
            from_=from_whatsapp,
            content_sid=content_sid,
            content_variables=content_variables,
            to=receiver,
        )


def send_call_notification(client, call_url, phone_numbers, from_number="+1234567890"):
    """
    Initiates voice calls via Twilio.

    :param client: An instance of twilio.rest.Client
    :param call_url: The URL containing TwiML instructions or a Twilio bin URL
    :param phone_numbers: List of phone numbers to call (e.g., ["+911234567890"])
    :param from_number: Your Twilio phone number
    """
    for receiver in phone_numbers:
        client.calls.create(from_=from_number, to=receiver, url=call_url)


def send_all_notifs(
    incident_id, incident_type, phone, email, camera_name, camera_location, time
):
    """
    Sends notifications through all available channels (email, SMS, WhatsApp, and call).

    Args:
        incident_id: ID of the incident
        incident_type: Type of incident
        phone: Recipient's phone number
        email: Recipient's email address
    """
    try:
        # Prepare common content
        url = reverse("resolve", args=[incident_id])
        main_text = f"Dear Surakshak,\n\nPlease check out the incident snippet and other information at {url} to resolve the alert as soon as possible. \n\nIncident Type: {incident_type} \nDetected at: {camera_location} \n Detected from Camera: {camera_name} \n Time: {time} \n\nRegards, \nInstitution"
        subject = f"Alert! Incident Type: {incident_type} Detected at {camera_location} from {camera_name}"

        # Initialize Twilio client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_client = Client(account_sid, auth_token)

        # Format phone number for different services
        formatted_phone = f"+91{phone}" if phone else None
        whatsapp_phone = f"whatsapp:+91{phone}" if phone else None

        # Send email notification
        if email:
            try:
                send_email_notification(
                    subject=subject,
                    body=main_text,
                    recipients=[email],
                    from_email="abhinavkun26@gmail.com",
                )
            except Exception as e:
                print(f"Failed to send email notification: {e}")

        # Send SMS notification
        if formatted_phone:
            try:
                send_sms_notification(
                    client=twilio_client,
                    body=main_text,
                    phone_numbers=[formatted_phone],
                    from_number="+12317666829",
                )
            except Exception as e:
                print(f"Failed to send SMS notification: {e}")

        # Send WhatsApp notification
        if whatsapp_phone:
            try:
                print("Sending WhatsApp notification")
                send_whatsapp_notification(
                    client=twilio_client,
                    content_sid="HXb5b62575e6e4ff6129ad7c8efe1f983e",
                    content_variables='{"1":"12/1","2":"3pm"}',
                    phone_numbers=[whatsapp_phone],
                    from_whatsapp="whatsapp:+14155238886",
                )
            except Exception as e:
                print(f"Failed to send WhatsApp notification: {e}")

        # Send call notification
        if formatted_phone:
            try:
                url = os.getenv("TwiML_BIN_URL")
                send_call_notification(
                    client=twilio_client,
                    call_url=url,
                    phone_numbers=[formatted_phone],
                    from_number="+12317666829",
                )
            except Exception as e:
                print(f"Failed to send call notification: {e}")

        return True

    except Exception as e:
        print(f"Failed to send notifications: {e}")
        return False
