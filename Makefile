# Vice Fjord: tynne innpakninger rundt det som finnes (npm run og python), så de vanligste
# kommandoene er like for alle, uansett språk. Make er valgfritt: npm run og python virker
# helt uten denne filen (Make finnes ikke på alle maskiner, særlig Windows uten WSL).
#
# .env (crewkoden, BYEN_URL osv.) leses inn hvis den finnes, så `make mcp` kan skrive ut den
# ferdige kommandoen uten at dere limer inn crewkoden selv.
-include .env

BYEN_URL ?= https://byen.hackaton.dev
OPPDRAG ?= kureren
VARIANT ?=

# .env tillater fnutter rundt verdien (CREW="kode" eller CREW='kode'), som dotenv i Node og Python
# fjerner. Make tar dem med i verdien, så de fjernes her før `make mcp` bruker dem.
fjern_fnutter = $(patsubst '%',%,$(patsubst "%",%,$(strip $(1))))
CREW_REN = $(call fjern_fnutter,$(CREW))
BYEN_URL_REN = $(call fjern_fnutter,$(BYEN_URL))

.PHONY: hjelp sjekk agent python mcp
.DEFAULT_GOAL := hjelp

hjelp: ## Lister målene (standard, uten argument)
	@echo "Mål:"
	@echo "  make sjekk    npm run sjekk: nøkkelen, modellen, byen og crewkoden"
	@echo "  make agent    eksempelagenten i Node. OPPDRAG=<oppdrag> (standard kureren), VARIANT=skjult for den skjulte ruten"
	@echo "  make python   den samme agenten, i Python"
	@echo "  make mcp      skriver ut «claude mcp add» for den felles MCP-adressen /mcp (krever CREW i .env)"
	@echo ""
	@echo "Eksempel: make agent OPPDRAG=flukt VARIANT=skjult"

sjekk: ## npm run sjekk
	npm run sjekk

agent: ## eksempelagenten i Node: make agent OPPDRAG=flukt VARIANT=skjult
	VARIANT=$(VARIANT) npm run agent -- $(OPPDRAG)

python: ## den samme agenten i Python: make python OPPDRAG=flukt VARIANT=skjult
	VARIANT=$(VARIANT) python3 agent/python/agent.py $(OPPDRAG)

mcp: ## claude mcp add for den felles MCP-adressen /mcp (krever CREW i .env)
	@if [ -z "$(CREW_REN)" ]; then \
		echo "Sett CREW i .env til crewkoden fra lappen."; \
		exit 1; \
	fi
	@echo 'claude mcp add --transport http vice-fjord "$(BYEN_URL_REN)/mcp?crew=$(CREW_REN)"'
