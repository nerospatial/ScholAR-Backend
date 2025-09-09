# Outbound primitives we send to the client
READY              = {"type": "ready"}
TYPE_SESSION_ID    = "session_id"
TYPE_TURN_COMPLETE = "turn_complete"
TYPE_TEXT          = "text"
TYPE_INTERRUPTED   = "interrupted"

# Inbound primitives we expect from the client
TYPE_END      = "end"
TYPE_TEXT_IN  = "text"  # {"type":"text","data":"..."}
