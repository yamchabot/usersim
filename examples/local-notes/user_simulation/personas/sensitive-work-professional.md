# Persona: The Sensitive-Work Professional

## Metrics That Matter to This User

| Metric | Constraint | Why It Matters |
|--------|-----------|----------------|
| `outbound_request_count` | == 0 | Client information must never be transmitted — zero requests is non-negotiable |
| `typing_request_count` | == 0 | Any request during a client conversation is a potential compliance violation |
| `auth_prompt_count` | == 0 | No authentication means no account, no vendor, no data processor |
| `account_prompt_count` | == 0 | An account ties the user's identity to the notes — unacceptable for client work |
| `external_service_call_count` | == 0 | No vendor means no DPA, no security review, no subprocessor disclosure required |
| `notebook_count` | ≥ 1 | One notebook per client or case ensures clean data separation |
| `shared_notebook_key_count` | == 0 | Structural isolation is stronger than permission-based isolation — it can't be misconfigured |
| `storage_error_count` | == 0 | The entire data boundary depends on localStorage working correctly |
| `external_resource_count` | == 0 | External resources reveal usage patterns and could theoretically exfiltrate content |
| `reload_loss_count` | == 0 | Notes from a client session must persist — losing them is a professional failure |

---

## User Benefits — How the App Delivers Them

---

**1. I take notes freely during client conversations without worrying about what I'm consenting to in the terms of service**

There is no terms of service governing your notes. The app makes no network requests and has no vendor relationship with the data you type into it. Your notes are browser data — legally and technically equivalent to something you typed into a local text editor. No consent framework applies because no data leaves your machine.

---

**2. I have a clear, defensible answer if anyone asks where client information was stored**

"In my browser's local storage, on my device, never transmitted anywhere." That answer is simple, accurate, and verifiable. You can demonstrate it by opening the browser's developer tools and showing that localStorage contains your notes and no network activity occurs while you type. It's the kind of answer a compliance review or client inquiry can accept without follow-up questions.

---

**3. I stop self-censoring my own notes because the tool makes me nervous**

When you're not sure who can read your notes or what the vendor does with them, you write less. You hedge. You leave out the important details. With this app, the anxiety is gone — and the notes become more accurate, more complete, and more useful. Better notes lead directly to better work.

---

**4. I can show a compliance officer exactly where the data lives — it's right there, in the browser, nowhere else**

If your organisation requires data location documentation, the answer is a browser and a device — both of which you already control. There's no cloud region to specify, no vendor DPA to negotiate, no subprocessor list to review. The data boundary is the browser, and the browser is on your machine.

---

**5. I don't have to file a vendor security review to start using a notes tool**

Because there's no vendor involved — no SaaS contract, no API key, no data processing agreement — the normal procurement and security review process doesn't apply. You open the file and use it. This matters in organisations where adding a new tool requires months of review. Local Notes sidesteps the entire process by having no vendor relationship to review.

---

**6. I keep separate notebooks per client or matter without any of them commingling on a shared server**

You create one notebook per client, case, or matter. Each notebook's notes are stored separately under their own localStorage key. There's no shared database where a misconfiguration could expose one client's notes to another. The separation is structural and permanent — not a permission setting that could be changed.

---

**7. I write better notes because I'm not editing myself — and better notes mean better work**

The quality of professional work often depends on the quality of the notes taken during it. When a tool is trusted completely, notes are written fully — with the candid observations, the sensitive details, the things that matter. That completeness compounds over time into a record that's genuinely useful, rather than a sanitised summary that protects no one and helps no one.
