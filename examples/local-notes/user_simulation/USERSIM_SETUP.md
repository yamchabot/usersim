# Usersim Setup — Local Notes
> How we approached modeling usersim for this application. No programming yet —
> these brainstorming steps are the foundation everything else builds on.

---

## Steps Taken

**1. Built the prototype first**
We made the actual app before thinking about users at all. A working thing to reason about is more honest than a spec. The prototype gave us something concrete to attach user thinking to.

**2. Identified user types from the outside in**
We didn't start with features. We started with people — who would want this kind of app, and why. The list came from imagining real contexts: privacy anxiety, professional risk, developer habits, frustration with existing tools.

**3. Selected a representative subset**
Not every user type is equally interesting or distinct. We picked 5 whose perspectives don't overlap much — they care about different things for different reasons. That diversity will matter later when constraints disagree.

**4. Named what each user gets out of the app**
We wrote User Benefits — not feature descriptions, not use cases. Statements in the user's voice about what changes for them. This forced us to think from their perspective rather than the product's.

**5. Expanded each benefit into how the app delivers it**
The persona files translate each benefit into the specific behavior of this specific app that enables it. Still not code — but grounded in the app's actual mechanics. This is where "localStorage only" goes from a technical choice to a user-meaningful thing.

**6. Derived measurable quantities from the benefit descriptions**
We read the persona files and asked: what would you actually observe to know this benefit is being delivered? This produced a list of things you can instrument — counts, timings, derived values. No booleans, because booleans are answers and we're not at answers yet.

**7. Pushed booleans out of the measurement layer**
When we found boolean metrics, we converted them to counts. `auth_required: false` became `auth_prompt_count == 0`. The distinction matters: measurements report what happened, constraints decide if that's acceptable.

**8. Named the perceptions as transformation functions**
Perceptions are the layer between raw measurements and user judgements. We named them as verb phrases — what the function *does* to arrive at its value. `detecting`, `measuring`, `inferring`. The verb tells you what kind of transformation it is.

**9. Mapped perceptions to their input metrics**
Each perception draws from specific metrics. Some metrics feed multiple perceptions. Some perceptions are composites of others. Making this explicit shows where the model is dense and where it's sparse.

**10. Sketched the instrumentation behind each perception**
We worked backwards from what each perception needs to know, to what browser automation would actually do to collect it. This is still design — no code yet — but it exposes real constraints: timing of script injection, the offline scenario needing an isolated run, patching localStorage before the app initialises.

---

## The Through-Line

Every step moves one layer deeper:

**People → Benefits → App behavior → Observable facts → Transformation functions → Collection methods**

Each layer is grounded in the one above it, and nothing was invented that wasn't earned by what came before.
