from app.core.smtp_config import conf as conf
from fastapi_mail import FastMail, MessageSchema

fast_mail = FastMail(conf)

async def send_email_async(to: str, subject: str, body: str) -> bool:
	message = MessageSchema(
		subject=subject,
		recipients=[to],
		body=body,
		subtype="plain"
	)
	try:
		await fast_mail.send_message(message)
		return True
	except Exception as e:
		print(f"FastAPI-Mail send failed: {e}")
		return False
