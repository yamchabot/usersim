# Persona: The Privacy-First User

## Metrics That Matter to This User

| Metric | Expected Value | Why It Matters |
|--------|---------------|----------------|
| `outbound_request_count` | 0 | Any request is a data leak — zero is the only acceptable number |
| `requests_on_load` | 0 | Nothing should phone home even before the user types |
| `requests_while_typing` | 0 | Keystroke-level telemetry is the worst-case scenario |
| `external_resource_count` | 0 | External scripts could exfiltrate data; fonts/CDNs reveal usage to third parties |
| `auth_required` | false | An account means a database row with their identity attached to their notes |
| `account_required` | false | Same — no account means no profile to breach or sell |
| `vendor_dependency` | false | If a vendor is required, that vendor has leverage over your data |
| `runs_offline` | true | Offline capability is proof that no server involvement is required |
| `localstorage_available` | true | Data must stay local — localStorage is the mechanism |
| `data_survives_reload` | true | Persistence without a server is the core value exchange |

---

## User Benefits — How the App Delivers Them

---

**1. I know with certainty that my notes have never touched a server I don't control**

The app is a single HTML file. There is no backend, no API, no sync service. When you open it, nothing is sent anywhere. You can open your browser's network inspector while using the app and watch zero outgoing requests — your notes go straight into your browser's localStorage and stay there. The certainty is verifiable, not a policy promise.

---

**2. I stop trading convenience for surveillance — I get both**

The app opens instantly, remembers all your notebooks and notes across sessions, and requires no setup. The convenience is identical to a cloud app — minus the account. You get the "it just works" experience without handing over your data to get it.

---

**3. I can write freely without wondering who might read it, sell it, or subpoena it**

Because notes live only in your browser, the only way someone else reads them is if they have physical access to your device. There are no terms of service governing your notes, no privacy policy to read, no data retention schedule. What you write is yours in the most literal sense.

---

**4. I don't need an account, which means there's no profile to breach, sell, or deactivate**

Opening the app requires nothing — no email address, no password, no OAuth flow. There is no account to be hacked, no subscription to be cancelled, no database row with your name on it. You open a tab and you're in.

---

**5. I have a notes tool that still works even if the company behind it disappears tomorrow**

The app is self-contained. Once the file is in your browser or saved to disk, it has no dependency on any external service. There is nothing to go offline, no login server to stop responding, no API to be deprecated. It will work in ten years exactly as it works today.

---

**6. I stop paying a monthly fee to rent access to my own thoughts**

There is no subscription, no free tier with limits, no upgrade prompt. The app costs nothing and has no concept of a paid plan. Your notebooks and notes are not stored on someone else's infrastructure — so no one can hold them hostage behind a paywall.

---

**7. I trust the tool completely, which means I actually use it — instead of keeping sensitive things in my head**

Because the privacy model is simple and verifiable, there's no nagging doubt when writing something sensitive. That trust removes the friction of self-censorship. Notes that would otherwise stay unwritten — because no tool felt safe enough — get written, organised, and actually useful.
