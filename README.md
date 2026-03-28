# QuMUD

[![Status](https://img.shields.io/badge/status-work--in--progress-orange)](#)
[![Stack](https://img.shields.io/badge/stack-Django%20%7C%20HTMX%20%7C%20PostgreSQL-green)](#)

QuMUD (Quantum MUD) is a procedurally generated multiplayer RPG with idle/autobattle combat and a focus on exploration, loot, and character building.

Combat events happen in real time, but are not simulated until requested (or "observed" hence the Quantum name).  Eventually the entire game will be playable via API as an alternative to the stock web app. 

---
### Current Features
- Basic user auth
- Character creation from preset class choices
- Can create or join existing Worlds by name
- Worlds generate procgen starting region, town, dungeons, enemy templates
- Can see other active players in region and chat with them
- Combat event instance creation, matching with other players, and simulation of entity movement and damage
- Players gain XP from defeated enemies and can level up
---

### In Progress Features
- **Menu overhaul:** Cleanup and standardization of navbar elements and menu flow/layout
- **Event/Combat logic:** Combat events with multiplayer support are currently simulated with random movement and damage updates, will implement actual combat logic next
---

### What's next?
- **True Combat:** Autobattle combat between players and enemies with realtime updates
- **Loot:** Random loot drops, item and equipment management
- **Expanded world:** Connected regions scaling by level
- **REST API:** Game fully playable via API calls, allowing playability via third party frontends or CLI
---

## 🛠️ Project Stack

This project is being built using Django, HTMX, vanilla JavaScript, and Bootstrap 5.

QuMUD is intentionally simplistic and seeks to do as much as possible with hypertext, HTTP requests and, eventually, optional REST API. 

- **Backend:** [Django 6.0](https://www.djangoproject.com/)
- **API:** [Django REST Framework](https://www.django-rest-framework.org)
- **Frontend:** [HTMX](https://htmx.org/), Django Templates, Javascript
- **CSS:** [Bootstrap 5](https://getbootstrap.com/)
- **Database:** [PostgreSQL](https://www.postgresql.org)