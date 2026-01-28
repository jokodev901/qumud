# QuMUD

[![Status](https://img.shields.io/badge/status-work--in--progress-orange)](#)
[![Stack](https://img.shields.io/badge/stack-Django%20%7C%20HTMX%20%7C%20Bootstrap-green)](#)

QuMUD (Quantum MUD) is a minimalist text-based procedurally generated multiplayer RPG with automated combat and a focus on exploration, loot, and character building.

Combat events are based on realtime server ticks, but are not simulated until requested (or "observed" hence the Quantum name).  Eventually the entire game will be playable via API as an alternative to the stock web app. 

---

## Overview

QuMUD is currently under active development, with the current focus on standing up a stripped down web app to demonstrate and test the core systems. 

### In Progress Features
- **User Authentication:** User registration, login, and Player alias management via Django auth.
- **Character Creation:** A temporary character creation template is in place, will be replaced with a more robust class/stat-based system.  
- **World Creation:** Game worlds are generated via seed (world name), currently implementing Region and location generation.

---

### What's next?
- **Events:**  Placeholder towns and working "dungeon" event areas with enemies and combat.
- **Stat system:**  Initial implementation of character building with stat weights and xp/levelling system
- **Loot:**  Initial item system with placeholder equipment 

---

## 🛠️ The Stack

This project is being built using Django, HTMX, and Bootstrap, focusing on server-side state and low-latency interactions.

- **Backend:** [Django 5.x](https://www.djangoproject.com/)
- **API:** [Django REST Framework](https://www.django-rest-framework.org)
- **Frontend:** [HTMX](https://htmx.org/), Django Templates
- **CSS:** [Bootstrap 5](https://getbootstrap.com/)
- **Database:** [PostgreSQL](https://www.postgresql.org)