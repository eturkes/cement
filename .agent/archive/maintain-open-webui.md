# MAINTAIN — Open WebUI live testing (closed Tasks rows)

Request: test Cement live on the Kimi K2.6 Open WebUI target with gpt-6-luna as stand-in (rulings = `.agent/spec.md` `Decisions` "Open WebUI deployment"). Live record = `.agent/decisions/owui-live-e2e.md`; review = `.agent/review.md` section "MAINTAIN Open WebUI live testing".

- [x] 5a236bf W1 paste-in generator: `examples/open_webui/` sources → `examples/open_webui/paste-in/*.py`, each embedding `cement_runtime` as readable source under a digest-named private package; freshness + self-containment (no installed `cement_runtime`) tests.
- [x] 990ec8d W2 chat side: filter inlet note (operations valve → name + input/output shape), tool refusal names the enabled operations; red-first tests.
- [x] fa25a60 W3 learning tool (admin-only; reviewer fixed `learning-pass`; no switch path) + the Open WebUI Skill text; tests.
- [x] b832321 W4 admin Action: create the ledger + register valve operations, switch off | follow | pinned through a select + confirmation, admin role checked, decline writes nothing; tests.
- [x] 15fd5b3 W5 local regimen launcher (Open WebUI 0.12.3, Python 3.11, any OpenAI-compatible endpoint + model) provisioning every paste-in, the skill and two workspace models; example README walkthrough.
- [x] 6fdbb26 W6 live end-to-end with `gpt-6-luna`: real prompts retained → learning pass promotes → switch on through the Action → a chat tool call returns `covered: true`; screenshots + record; review section; full gate.
