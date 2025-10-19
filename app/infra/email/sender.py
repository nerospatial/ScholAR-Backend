from app.infra.email.providers.smtp import send_email_async

class EmailSender:
	async def send_verification_code(self, to: str, subject: str, body: str) -> bool:
		"""Send an email asynchronously using FastAPI-Mail."""
		return await send_email_async(to, subject, body)

# Example usage:
# sender = EmailSender()
# await sender.send("recipient@example.com", "Subject", "Body text")
