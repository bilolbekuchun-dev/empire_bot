# Redis Game Architecture & Migration TODO

## 📦 Yangi Package Strukturasi

```
utils/redis_game/
├── __init__.py                    # Public API exports
├── game_models_schema.py          # ✅ Pydantic models (GameState, PlayerState)
├── game_models_crud.py            # ✅ Basic CRUD (RedisStateManager)
├── utils.py                       # ✅ Helper functions (permissions, etc.)
│
├── repositories/                  # ✅ Data Access Layer - COMPLETED
│   ├── __init__.py               # ✅ 
│   ├── game_repository.py        # ✅ Game Redis operations
│   └── player_repository.py      # ✅ Player Redis operations
│
└── services/                      # ✅ Business Logic Layer - STARTED
    ├── __init__.py               # ✅
    ├── game_service.py           # ✅ Game lifecycle (create, end)
    ├── player_service.py         # ✅ Player management (join, leave)
    ├── phase_service.py          # ❌ TODO - Phase management
    ├── action_service.py         # ❌ TODO - Actions (kill, heal, etc.)
    └── vote_service.py           # ❌ TODO - Voting system
```

## ✅ Tayyor bo'lgan

### Repositories Layer
- ✅ `GameRepository` - game CRUD, active games, cleanup
- ✅ `PlayerRepository` - player CRUD, sets, balls, statistics

### Services Layer  
- ✅ `GameService` - create_game, end_game, save_to_db
- ✅ `PlayerService` - join_game, leave_game, get_statistics

### Utils
- ✅ `check_user_permission` - ruxsat tekshirish

---

## 📋 TODO: Keyingi Qadamlar

### 1. PhaseService yaratish ⏳
**Fayl:** `services/phase_service.py`

**Funksiyalar:**
```python
- create_phase(game_id, phase_type, phase_num)
- get_current_phase(game_id)
- transition_to_night(game_id)
- transition_to_day(game_id)
- end_phase(game_id, phase_num)
```

**Qayerdan ko'chirish:** `game_logic.py` dan phase bilan bog'liq funksiyalar

---

### 2. ActionService yaratish ⏳
**Fayl:** `services/action_service.py`

**Funksiyalar:**
```python
- save_action(game_id, phase_id, actor_id, target_id, action_type)
- get_phase_actions(game_id, phase_id)
- process_night_actions(game_id, phase_id)
- apply_kill_action(game_id, target_id)
- apply_heal_action(game_id, target_id)
- apply_protect_action(game_id, target_id)
- apply_investigate_action(game_id, target_id)
```

**Qayerdan ko'chirish:** 
- `game_logic.py` - `tungi_harakat`, `view_night_results`
- `night_actions.py` - barcha action funksiyalari

---

### 3. VoteService yaratish ⏳
**Fayl:** `services/vote_service.py`

**Funksiyalar:**
```python
- save_vote(game_id, phase_id, voter_id, target_id)
- get_vote_results(game_id, phase_id)
- process_day_vote(game_id, phase_id)
- process_mafia_vote(game_id, phase_id)
- save_vote_like(game_id, phase_id, voter_id, target_id, is_like)
- get_vote_like_results(game_id, phase_id)
```

**Qayerdan ko'chirish:**
- `game_logic.py` - `stop_voting_mafias`, `vote_like_action`, `handle_vote_like`

---

### 4. game_frame.py ni refactor qilish ⏳
**Maqsad:** Eski `game_frame.py` dan yangi service/repository larga ko'chirish

**O'chirish kerak:**
- ✅ `generate_game_id` → `game_repository.generate_id()`
- ✅ `check_permissions` → `utils.check_user_permission()`
- ✅ `get_active_game` → `game_repository.get_active_game()`
- ✅ `add_active_game` → `game_repository.add_active_game()`
- ✅ `remove_active_game` → `game_repository.remove_active_game()`
- ✅ `create_game_handler` → `game_service.create_game()`
- ✅ `join_player_to_game` → `player_service.join_game()`
- ✅ `get_game_players` → `player_repository.get_all_players()`
- ✅ `get_game_players_count` → `player_repository.get_players_count()`
- ✅ `remove_player_from_game` → `player_service.leave_game()`
- ✅ `end_game` → `game_service.end_game()`
- ✅ `set_player_ball` → `player_repository.set_ball()`
- ✅ `get_player_ball` → `player_repository.get_ball()`
- ✅ `increment_player_ball` → `player_repository.increment_ball()`
- ✅ `update_player_profile_after_game` → `player_service.update_player_profile()`
- ✅ `get_game_statistics` → `player_service.get_game_statistics()`

**Natija:** `game_frame.py` ni o'chirish yoki deprecated qilish

---

### 5. Existing handlers ni yangilash ⏳
**Fayl:** `handlers/game.py` va boshqalar

**O'zgartirishlar:**
```python
# Eski:
from utils.redis_game.game_frame import create_game_handler

# Yangi:
from utils.redis_game.services import game_service

# Ishlatish:
await game_service.create_game(message, bot, is_vs_game=False)
```

---

### 6. game_logic.py ni bosqichma-bosqich migratsiya qilish ⏳

**Phase 1:** Game yaratish
- ✅ `create_game_handler` → `game_service.create_game`
- ✅ `create_vs_game_handler` → `game_service.create_game`

**Phase 2:** Player management
- ✅ `join_game_handler` → `player_service.join_game`
- ✅ `leave_game` → `player_service.leave_game`

**Phase 3:** Game start
- ⏳ `starting_game` → `game_service.start_game`
- ⏳ `rol_taqsimlash` → `game_service.assign_roles`

**Phase 4:** Phase management
- ⏳ `tungi_harakat` → `phase_service.transition_to_night`
- ⏳ `day_action` → `phase_service.transition_to_day`

**Phase 5:** Actions & Votes
- ⏳ `stop_voting_mafias` → `vote_service.process_mafia_vote`
- ⏳ `view_night_results` → `action_service.process_night_actions`

**Phase 6:** Game end
- ✅ `announce_game_result` → `game_service.end_game` (partial)
- ⏳ Winner detection logic → `game_service.detect_winner`

---

### 7. Testing ⏳
**Test fayllar yaratish:**
```
tests/redis_game/
├── test_game_repository.py
├── test_player_repository.py
├── test_game_service.py
└── test_player_service.py
```

---

### 8. Public API (__init__.py) ⏳
**Fayl:** `utils/redis_game/__init__.py`

```python
# Clean public API
from .services import game_service, player_service
from .repositories import game_repository, player_repository
from .utils import check_user_permission

__all__ = [
    'game_service',
    'player_service',
    'game_repository',
    'player_repository',
    'check_user_permission',
]
```

---

## 🎯 Prioritet

1. **HIGH** - PhaseService (o'yin davom etishi uchun kerak)
2. **HIGH** - ActionService (tungi harakatlar)
3. **MEDIUM** - VoteService (ovoz berish)
4. **MEDIUM** - game_frame.py refactor
5. **LOW** - Testing
6. **LOW** - Documentation

---

## 📊 Progress

- ✅ Repositories: **100%** (2/2)
- ⚙️ Services: **40%** (2/5)
- ⏳ Migration: **20%** (game yaratish/tugatish)
- ⏳ Testing: **0%**

---

## 💡 Keyingi Qadam

**Start here:** `services/phase_service.py` yaratish

Keyin `action_service.py` va `vote_service.py` ni davom ettirish.
