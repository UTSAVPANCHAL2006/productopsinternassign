"""Fetch and clean developer-doc text for an app."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

USER_AGENT = (
    "ComposioToolkitResearchBot/1.0 (+ops-intern-assignment; research only)"
)

# Candidate doc URL patterns derived from assignment hints + common conventions.
DOC_CANDIDATES: dict[str, list[str]] = {
    "Salesforce": [
        "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_oauth_and_connected_apps.htm",
        "https://developer.salesforce.com/docs",
    ],
    "HubSpot": [
        "https://developers.hubspot.com/docs/api/overview",
        "https://developers.hubspot.com/docs/api/oauth-quickstart-guide",
    ],
    "Pipedrive": ["https://developers.pipedrive.com/docs/api/v1"],
    "Attio": ["https://developers.attio.com/docs/overview", "https://developers.attio.com/reference"],
    "Twenty": ["https://docs.twenty.com/developers/api", "https://twenty.com"],
    "Podio": ["https://developers.podio.com/"],
    "Zoho CRM": ["https://www.zoho.com/crm/developer/docs/api/v6/"],
    "Close": ["https://developer.close.com/"],
    "Copper": ["https://developer.copper.com/"],
    "DealCloud": ["https://api.docs.dealcloud.com/"],
    "Zendesk": ["https://developer.zendesk.com/api-reference/"],
    "Intercom": ["https://developers.intercom.com/docs"],
    "Freshdesk": ["https://developers.freshdesk.com/api/"],
    "Front": ["https://dev.frontapp.com/"],
    "Pylon": ["https://docs.usepylon.com/", "https://usepylon.com"],
    "LiveAgent": ["https://support.liveagent.com/741162-API"],
    "Plain": ["https://www.plain.com/docs/graphql", "https://www.plain.com/docs"],
    "Help Scout": ["https://developer.helpscout.com/"],
    "Gorgias": ["https://developers.gorgias.com/"],
    "Gladly": ["https://developer.gladly.com/"],
    "Slack": ["https://api.slack.com/authentication", "https://api.slack.com/"],
    "Twilio": ["https://www.twilio.com/docs/usage/api", "https://www.twilio.com/docs"],
    "Zoho Cliq": ["https://www.zoho.com/cliq/help/restapi/"],
    "Lark (Larksuite)": ["https://open.larksuite.com/document/"],
    "Pumble": ["https://pumble.com/api/", "https://pumble.com/help/integrations/api/"],
    "Discord": ["https://discord.com/developers/docs/intro"],
    "Telegram": ["https://core.telegram.org/bots/api"],
    "WhatsApp Business": ["https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"],
    "Aircall": ["https://developer.aircall.io/"],
    "Vonage": ["https://developer.vonage.com/en/getting-started/overview"],
    "Google Ads": ["https://developers.google.com/google-ads/api/docs/start"],
    "Meta Ads": ["https://developers.facebook.com/docs/marketing-apis/"],
    "LinkedIn Ads": ["https://learn.microsoft.com/en-us/linkedin/marketing/"],
    "GoHighLevel": ["https://highlevel.stoplight.io/docs/integrations/"],
    "Mailchimp": ["https://mailchimp.com/developer/marketing/"],
    "Klaviyo": ["https://developers.klaviyo.com/en"],
    "systeme.io": ["https://developer.systeme.io/", "https://systeme.io"],
    "Pinterest": ["https://developers.pinterest.com/docs/api/v5/"],
    "Threads (Meta)": ["https://developers.facebook.com/docs/threads"],
    "SendGrid": ["https://docs.sendgrid.com/api-reference"],
    "Shopify": ["https://shopify.dev/docs/api"],
    "WooCommerce": ["https://woocommerce.com/document/woocommerce-rest-api/"],
    "BigCommerce": ["https://developer.bigcommerce.com/docs/rest-catalog"],
    "Salesforce Commerce Cloud": ["https://developer.salesforce.com/docs/commerce"],
    "Magento (Adobe Commerce)": ["https://developer.adobe.com/commerce/webapi/get-started/"],
    "Squarespace": ["https://developers.squarespace.com/commerce-apis/"],
    "Ecwid": ["https://api-docs.ecwid.com/"],
    "Gumroad": ["https://gumroad.com/api"],
    "Amazon Selling Partner": ["https://developer-docs.amazon.com/sp-api/docs"],
    "fanbasis": ["https://fanbasis.com/", "https://docs.fanbasis.com/"],
    "DataForSEO": ["https://docs.dataforseo.com/v3/"],
    "SE Ranking": ["https://seranking.com/api.html"],
    "Ahrefs": ["https://ahrefs.com/api"],
    "MrScraper": ["https://docs.mrscraper.com/"],
    "Apify": ["https://docs.apify.com/api/v2"],
    "Firecrawl": ["https://docs.firecrawl.dev/"],
    "Bright Data": ["https://docs.brightdata.com/"],
    "Sherlock": ["https://github.com/sherlock-project/sherlock"],
    "Waterfall.io": ["https://waterfall.io/", "https://docs.waterfall.io/"],
    "Clay": ["https://www.clay.com/", "https://docs.clay.com/"],
    "GitHub": ["https://docs.github.com/en/rest", "https://docs.github.com/en/rest/authentication"],
    "Vercel": ["https://vercel.com/docs/rest-api"],
    "Netlify": ["https://docs.netlify.com/api/get-started/"],
    "Cloudflare": ["https://developers.cloudflare.com/api/"],
    "Supabase": ["https://supabase.com/docs/reference/api/introduction"],
    "Neo4j": ["https://neo4j.com/docs/http-api/current/"],
    "Snowflake": ["https://docs.snowflake.com/en/developer-guide/sql-api/index"],
    "MongoDB Atlas": ["https://www.mongodb.com/docs/atlas/api/atlas-admin-api/"],
    "Datadog": ["https://docs.datadoghq.com/api/"],
    "Sentry": ["https://docs.sentry.io/api/"],
    "Notion": ["https://developers.notion.com/reference/intro", "https://developers.notion.com/docs/authorization"],
    "Airtable": ["https://airtable.com/developers/web/api/introduction"],
    "Linear": ["https://developers.linear.app/docs", "https://developers.linear.app/docs/graphql/working-with-the-graphql-api"],
    "Jira": ["https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/"],
    "Asana": ["https://developers.asana.com/docs"],
    "Monday.com": ["https://developer.monday.com/api-reference/docs"],
    "ClickUp": ["https://clickup.com/api"],
    "Coda": ["https://coda.io/developers/apis/v1"],
    "Smartsheet": ["https://smartsheet.redoc.ly/"],
    "Harvest": ["https://help.getharvest.com/api-v2/"],
    "Stripe": ["https://docs.stripe.com/api", "https://docs.stripe.com/keys"],
    "Plaid": ["https://plaid.com/docs/api/"],
    "Binance": ["https://binance-docs.github.io/apidocs/spot/en/"],
    "Paygent Connect": ["https://secure.nmi.com/merchants/resources/integration/integration_portal.php"],
    "iPayX": ["https://ipayx.ai/docs", "https://ipayx.ai/"],
    "QuickBooks": ["https://developer.intuit.com/app/developer/qbo/docs/get-started"],
    "Xero": ["https://developer.xero.com/documentation/"],
    "Brex": ["https://developer.brex.com/"],
    "Ramp": ["https://docs.ramp.com/"],
    "PitchBook": ["https://pitchbook.com/products/data/platform-api", "https://pitchbook.com"],
    "NotebookLM": ["https://cloud.google.com/gemini/enterprise/docs", "https://blog.google/technology/ai/notebooklm-api/"],
    "Otter AI": ["https://otter.ai/mcp", "https://help.otter.ai/hc/en-us"],
    "Fathom": ["https://developers.fathom.ai/", "https://fathom.video"],
    "Consensus": ["https://consensus.app/", "https://github.com/consensus-org"],
    "Reducto": ["https://docs.reducto.ai/", "https://reducto.ai"],
    "Devin": ["https://docs.devin.ai/", "https://docs.devin.ai/work-with-devin/mcp"],
    "higgsfield": ["https://higgsfield.ai/cli", "https://higgsfield.ai"],
    "Mermaid CLI": ["https://github.com/mermaid-js/mermaid-cli"],
    "YouTube Transcript": ["https://transcriptapi.com/docs", "https://transcriptapi.com"],
    "Grain": ["https://grain.com/", "https://support.grain.com/"],
}


@dataclass
class FetchedDoc:
    url: str
    title: str
    text: str
    status_code: int
    ok: bool


def hint_to_urls(name: str, hint: str) -> list[str]:
    urls = list(DOC_CANDIDATES.get(name, []))
    # Pull bare domains / paths from hint
    for token in re.findall(r"[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[/\w.-]*", hint):
        if token.startswith("http"):
            urls.append(token)
        else:
            urls.append("https://" + token.rstrip(")"))
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:6]


def _clean_html(html: str, base_url: str) -> tuple[str, str]:
    import warnings
    from bs4 import XMLParsedAsHTMLWarning

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()
    title = (soup.title.get_text(strip=True) if soup.title else "")[:200]
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Keep enough signal for LLM without blowing context
    return title, text[:14000]


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.8, min=1, max=6))
def fetch_url(client: httpx.Client, url: str) -> FetchedDoc:
    try:
        resp = client.get(url, follow_redirects=True, timeout=25.0)
        content_type = resp.headers.get("content-type", "")
        if "html" in content_type or resp.text.lstrip().startswith("<"):
            title, text = _clean_html(resp.text, str(resp.url))
        else:
            title = urlparse(str(resp.url)).path
            text = resp.text[:14000]
        return FetchedDoc(
            url=str(resp.url),
            title=title,
            text=text,
            status_code=resp.status_code,
            ok=resp.status_code < 400 and len(text) > 80,
        )
    except Exception as exc:  # noqa: BLE001
        return FetchedDoc(url=url, title="", text=f"FETCH_ERROR: {exc}", status_code=0, ok=False)


def fetch_docs_for_app(name: str, hint: str, client: httpx.Client | None = None) -> list[FetchedDoc]:
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, http2=False)
    try:
        results: list[FetchedDoc] = []
        for url in hint_to_urls(name, hint):
            doc = fetch_url(client, url)
            results.append(doc)
            if doc.ok:
                # Prefer first good doc + one secondary if available
                if len([d for d in results if d.ok]) >= 2:
                    break
        return results
    finally:
        if own:
            client.close()


def pack_evidence(docs: Iterable[FetchedDoc], max_chars: int = 18000) -> tuple[str, list[str]]:
    chunks: list[str] = []
    urls: list[str] = []
    used = 0
    for d in docs:
        if d.ok:
            urls.append(d.url)
        block = f"URL: {d.url}\nSTATUS: {d.status_code}\nTITLE: {d.title}\n---\n{d.text}\n"
        if used + len(block) > max_chars:
            remain = max_chars - used
            if remain > 500:
                chunks.append(block[:remain])
            break
        chunks.append(block)
        used += len(block)
    return "\n\n".join(chunks), urls
