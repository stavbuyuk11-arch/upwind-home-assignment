import difflib
import re
def parse_email(file_path):
    sender = ""
    subject = ""
    attachments = []
    body_lines = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()

            if clean_line.startswith("From:"):
                sender = clean_line.split(":", 1)[1].strip()

            elif clean_line.startswith("Subject:"):
                subject = clean_line.split(":", 1)[1].strip()

            elif clean_line.startswith("Attachments:"):
                new_attachments = clean_line.split(":", 1)[1].strip()

                if new_attachments:
                    attachments = [a.strip() for a in new_attachments.split(",")]

            else:
                body_lines.append(clean_line)

    return {
        "sender": sender,
        "subject": subject,
        "attachments": attachments,
        "body": "\n".join(body_lines).strip()
    }




def check_sender(sender):
    reasons=[]
    if '@' not in sender:
        return 40,["invalid sender email format"]
    domain = sender.split("@")[-1].lower().strip()

    risky_tlds = (".xyz", ".top", ".click", ".tk", ".info")
    if domain.endswith(risky_tlds):
        reasons.append(f"Suspicious sender domain extension: {domain}")

    if domain.count("-") >= 2:
        reasons.append(f"Too many hyphens in sender domain: {domain}")

    if any(ch.isdigit() for ch in domain):
        reasons.append(f"Numbers found in sender domain: {domain}")

    normalized = domain.replace("0", "o").replace("1", "l").replace("3", "e").replace("5", "s")
    domain_parts = normalized.replace(".", "-").split("-")
    trusted_brands = {
        "paypal": "paypal.com",
        "amazon": "amazon.com",
        "aliexpress": "aliexpress.com",
        "israelpost": "israelpost.co.il",
        "google": "google.com",
        "microsoft": "microsoft.com",
    }

    for brand, official_domain in trusted_brands.items():
        if domain != official_domain:
            for part in domain_parts:
                if brand in part or difflib.SequenceMatcher(None, part, brand).ratio() >= 0.8:
                    reasons.append(f"Possible brand impersonation in sender: {domain}")
                    break

    score = 40 if reasons else 0
    return score, reasons


def check_attachments(attachments):
    reasons = []
    dangerous_extensions = (".exe", ".bat", ".cmd", ".scr", ".js", ".vbs", ".zip", ".rar")

    for filename in attachments:
        lower_name = filename.lower().strip()
        if lower_name.endswith(dangerous_extensions):
            reasons.append(f"Dangerous attachment extension: {filename}")
        elif lower_name.count(".") >= 2:
            reasons.append(f"Suspicious double extension in attachment: {filename}")

    score = 30 if reasons else 0
    return score, reasons


def check_links(body):
    reasons = []
    urls = re.findall(r"https?://[^\s]+", body)
    risky_tlds = (".xyz", ".top", ".click", ".tk", ".info")
    shorteners = ("bit.ly", "tinyurl.com", "t.co")

    for url in urls:
        lower_url = url.lower()
        if re.search(r"https?://\d+\.\d+\.\d+\.\d+", lower_url):
            reasons.append(f"Link uses an IP address instead of a domain: {url}")
        if lower_url.startswith("http://"):
            reasons.append(f"Unencrypted HTTP link: {url}")
        for tld in risky_tlds:
            if tld in lower_url:
                reasons.append(f"Suspicious domain extension in link: {url}")
                break
        for shortener in shorteners:
            if shortener in lower_url:
                reasons.append(f"Shortened URL detected: {url}")
                break

    score = 20 if reasons else 0
    return score, reasons


def check_wording(subject, body):
    reasons = []
    full_text = f"{subject} {body}".lower()
    suspicious_words = [
        "urgent", "immediately", "suspended", "verify", "click here",
        "24 hours", "payment", "customs", "locked", "password",
        "דחוף", "תשלום", "חבילה", "מכס", "לחסום", "אימות"
    ]

    found_words = []
    for word in suspicious_words:
        if word in full_text:
            found_words.append(word)

    if found_words:
        reasons.append(f"Suspicious wording found: {', '.join(found_words)}")

    score = 10 if reasons else 0
    return score, reasons


def analyze_email(file_path):
    email_data = parse_email(file_path)

    s_score, s_reasons = check_sender(email_data["sender"])
    a_score, a_reasons = check_attachments(email_data["attachments"])
    l_score, l_reasons = check_links(email_data["body"])
    w_score, w_reasons = check_wording(email_data["subject"], email_data["body"])

    total_score = s_score + a_score + l_score + w_score
    all_reasons = s_reasons + a_reasons + l_reasons + w_reasons
    is_phishing = total_score >= 50

    print("--- Phishing Scan Summary ---")
    print("From:", email_data["sender"])
    print("Subject:", email_data["subject"])
    print("Risk Score:", f"{total_score}/100")
    print("Likely Phishing:", "YES" if is_phishing else "NO")
    print("Detected Indicators:")
    if all_reasons:
        for reason in all_reasons:
            print(" -", reason)
    else:
        print(" -NONE")
    return{
            "sender":email_data["sender"],
            "subject":email_data["subject"],
            "score":total_score,
            "is_phishing":is_phishing,
            "reasons":all_reasons,
            "sender_score":s_score,
            "attachments_score":a_score,
            "links_score":l_score,
            "wording_score":w_score
        }
    if __name__=="__main__":
        analyze_email("email.txt")