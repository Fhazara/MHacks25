import requests
import json

def send_report_to_agentverse(report, url="https://agentverse-placeholder/api/report"):
    """
    Sends the report to the AgentVerse agent via HTTP POST.
    Args:
        report (dict or list): The report data to send.
        url (str): The endpoint URL of the AgentVerse agent.
    Returns:
        response: The requests.Response object.
    """
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(report), headers=headers)
        response.raise_for_status()
        print(f"Report sent successfully! Status code: {response.status_code}")
        return response
    except requests.RequestException as e:
        print(f"Failed to send report: {e}")
        return None
