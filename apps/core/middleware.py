import json

from django.contrib.messages import constants as message_constants
from django.contrib.messages import get_messages


LEVEL_TO_TONE = {
    message_constants.DEBUG: "neutral",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}


def _merge_hx_trigger(response, event_name, detail):
    existing = response.headers.get("HX-Trigger")
    if not existing:
        response.headers["HX-Trigger"] = json.dumps({event_name: detail})
        return

    try:
        payload = json.loads(existing)
        if not isinstance(payload, dict):
            payload = {str(existing): True}
    except json.JSONDecodeError:
        payload = {str(existing): True}

    current = payload.get(event_name)
    if isinstance(current, dict) and isinstance(detail, dict):
        if "messages" in current and "messages" in detail:
            current["messages"] = [*current["messages"], *detail["messages"]]
        else:
            current.update(detail)
        payload[event_name] = current
    else:
        payload[event_name] = detail

    response.headers["HX-Trigger"] = json.dumps(payload)


class HtmxToastMessagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.headers.get("HX-Request") != "true":
            return response

        queued_messages = [
            {
                "id": f"toast-{index}",
                "text": str(message),
                "tone": LEVEL_TO_TONE.get(message.level, "info"),
                "css_class": message.tags or "",
            }
            for index, message in enumerate(get_messages(request), start=1)
        ]
        if queued_messages:
            _merge_hx_trigger(response, "ui:toast", {"messages": queued_messages})
        return response
