# Game Logic Migration - Detailed Analysis & Plan

## 📊 Current State Analysis

**File:** `utils/game_logic.py`
- **Total Lines:** ~5075 lines (almost 5000+ lines!)
- **Functions:** 25+ async functions
- **Dependencies:** 
  - Tortoise ORM (Game, GamePlayer, GamePhase, Action, Vote, VoteLike)
  - Aiogram (Bot, Message, CallbackQuery)
  - Keyboards, Models, Utils

---

## 🔍 Function Dependency Map

### Level 1: Core Functions (No dependencies on other game functions)
```
✅ create_game_handler          → game_service.create_game
✅ create_vs_game_handler        → game_service.create_game(is_vs_game=True)
✅ leave_game                    → player_service.leave_game
```

### Level 2: Player Management
```
⏳ join_game_handler             → Dependencies: update_players_list, starting_game
⏳ update_players_list           → Dependencies: view_players_list
⏳ view_players_list             → Pure function (easy to migrate)
⏳ kick_player                   → Dependencies: update_players_list, starting_game, assign_new_role
```

### Level 3: Game Lifecycle
```
⏳ starting_game                 → CRITICAL - Dependencies:
   ├── rol_taqsimlash
   ├── check_and_replace_missing_roles
   ├── tungi_harakat
   ├── day_action
   ├── view_night_results
   ├── stop_voting_mafias
   ├── vote_like_action
   ├── announce_game_result
   └── sheriklar_text_sender

⏳ start_game_handler            → Dependencies: starting_game
⏳ stop_game_handler             → Dependencies: announce_game_result
```

### Level 4: Role Assignment
```
⏳ rol_taqsimlash                → Dependencies: ActiveRole, Profile, send messages
⏳ sheriklar_text_sender         → Dependencies: GamePlayer queries
⏳ assign_new_role               → Dependencies: rol_taqsimlash logic
```

### Level 5: Phase Management
```
⏳ tungi_harakat                 → Dependencies: Action, GamePhase, send_geroys_action_message
⏳ day_action                    → Dependencies: Vote, GamePhase, action_buttons
⏳ vote_like_action              → Dependencies: VoteLike, GamePhase
```

### Level 6: Results Processing
```
⏳ view_night_results            → HUGE (1400+ lines!) - Dependencies:
   ├── All action types (kill, heal, protect, investigate, etc.)
   ├── Role-specific logic (50+ roles)
   ├── GamePlayer updates
   ├── Bot messages
   └── assign_new_role

⏳ view_night_results_old        → Legacy version (backup)
⏳ stop_voting_mafias            → Dependencies: Vote queries, vote counting
⏳ handle_vote_like              → Dependencies: VoteLike, CallbackQuery
⏳ check_vote_like_result        → Dependencies: VoteLike, vote counting
```

### Level 7: Game Result
```
⏳ announce_game_result          → Dependencies:
   ├── PlayersGameBall
   ├── Profile updates
   ├── get_profile
   └── Complex winner detection logic

⏳ check_paralar_lst             → Para mode specific
⏳ check_mafialar_list           → Helper function
```

---

## 🎯 Migration Strategy

### ⚠️ CRITICAL RULES:
1. **NEVER modify game_logic.py directly**
2. **Create parallel Redis versions**
3. **Test each function independently**
4. **Keep backward compatibility**
5. **Use feature flags for gradual rollout**

---

## 📋 Phase-by-Phase Migration Plan

### **PHASE 0: Preparation** 🛠️
**Duration:** 1-2 days
**Risk:** Low

- [x] Create Redis architecture (DONE)
- [x] Create repositories (DONE)
- [x] Create services (DONE)
- [ ] Create test framework
- [ ] Create migration utilities
- [ ] Create feature flags system

**Deliverable:** Testing infrastructure ready

---

### **PHASE 1: Simple Handlers** ✅ (EASY)
**Duration:** 2-3 days
**Risk:** Low
**Status:** Partially Done

#### Functions to migrate:
1. **create_game_handler** → `game_service.create_game()`
   - ✅ Already created
   - [ ] Add feature flag
   - [ ] Test with real game
   
2. **create_vs_game_handler** → `game_service.create_game(is_vs_game=True)`
   - ✅ Already created
   - [ ] Add feature flag
   - [ ] Test with real VS game

3. **leave_game** → `player_service.leave_game()`
   - [ ] Implement Redis version
   - [ ] Test leave during waiting phase
   - [ ] Handle edge cases

**Testing Checklist:**
- [ ] Create game in test chat
- [ ] Join game
- [ ] Leave game
- [ ] Verify Redis data
- [ ] Verify cleanup

**Rollback Plan:** Switch feature flag off

---

### **PHASE 2: Player List Management** 📝 (MEDIUM)
**Duration:** 3-4 days
**Risk:** Medium

#### Functions to migrate:
1. **view_players_list** → Pure function
   ```python
   # utils/redis_game/services/player_list_service.py
   async def format_players_list(game_id: int, is_vs_game: bool)
   ```
   
2. **update_players_list** → `player_list_service.update_display()`
   - Dependencies: view_players_list, Bot
   - Needs: Message editing logic
   
3. **join_game_handler** → `player_service.join_game()` + update_players_list
   - Complex: Checks max players, starts game
   - Dependencies: starting_game (defer to Phase 4)

**Testing Checklist:**
- [ ] Join game with 1-15 players
- [ ] Check player list format
- [ ] Test VS game teams
- [ ] Test max players limit
- [ ] Verify message updates

**Rollback Plan:** Use old handler

---

### **PHASE 3: Kick Player & Basic Admin** 👮 (MEDIUM)
**Duration:** 2-3 days
**Risk:** Medium

#### Functions to migrate:
1. **kick_player** → `admin_service.kick_player()`
   - Dependencies: update_players_list, assign_new_role
   - Needs: Admin permission check
   - Phases: waiting vs active game

**New Service:**
```python
# utils/redis_game/services/admin_service.py
class AdminService:
    async def kick_player(game_id, user_id, admin_id)
    async def force_start(game_id, admin_id)
    async def force_stop(game_id, admin_id)
```

**Testing Checklist:**
- [ ] Kick during waiting
- [ ] Kick during active game
- [ ] Verify auto-start if max players
- [ ] Test assign_new_role (if kicked in-game)

**Rollback Plan:** Feature flag

---

### **PHASE 4: Game Start & Role Assignment** 🎲 (HIGH RISK)
**Duration:** 1-2 weeks
**Risk:** HIGH - This is the most critical part!

#### Functions to migrate:

1. **rol_taqsimlash** → `role_service.assign_roles()`
   - **CRITICAL:** 200+ lines, complex role logic
   - Dependencies: GameSetListRoles, ActiveRole, Profile
   - Roles: 50+ different roles with special logic
   
2. **sheriklar_text_sender** → `role_service.send_team_info()`
   - Send partner info to mafia/werewolves
   - Dependencies: GamePlayer queries

3. **starting_game** → `game_service.start_game()` + game loop
   - **HUGE:** 490+ lines!
   - Main game loop (night → day → vote → result)
   - Dependencies: ALL other functions
   
4. **start_game_handler** → Wrapper for starting_game

**Strategy: Split into sub-services**
```python
# utils/redis_game/services/role_service.py
class RoleService:
    async def assign_roles(game_id, player_ids)
    async def send_role_messages(game_id)
    async def send_team_info(game_id)
    async def get_active_roles(user_id)

# utils/redis_game/services/game_loop_service.py
class GameLoopService:
    async def start_game_loop(game_id)
    async def run_night_phase(game_id)
    async def run_day_phase(game_id)
    async def check_win_conditions(game_id)
```

**Testing Checklist:**
- [ ] Assign roles correctly (all role types)
- [ ] Send role messages
- [ ] Send team info (mafia, bori)
- [ ] Start game loop
- [ ] Test each phase transition
- [ ] Test win condition checking

**Rollback Plan:** 
- Keep game_logic.py active
- Use feature flag per chat
- Monitor logs carefully

---

### **PHASE 5: Night Actions** 🌙 (HIGH RISK)
**Duration:** 1-2 weeks
**Risk:** HIGH

#### Functions to migrate:

1. **tungi_harakat** → `phase_service.run_night_phase()`
   - Send action buttons to alive players
   - Track who acted
   - Handle role-specific actions
   
2. **view_night_results** → `action_result_service.process_night_results()`
   - **MASSIVE:** 1400+ lines!
   - 50+ role interactions
   - Kill/heal/protect logic
   - All role-specific abilities
   
**Strategy: Split by role categories**
```python
# utils/redis_game/services/night_action_handlers/
├── __init__.py
├── mafia_actions.py      # DON, MAFIA, OVCHI, etc.
├── tinch_actions.py      # DOKTOR, KOMISSAR, etc.
├── yakka_actions.py      # JOKER, QOTIL, BORI, etc.
└── special_actions.py    # Complex roles
```

**Testing Checklist:**
- [ ] Each role can act
- [ ] Action conflicts (kill + heal)
- [ ] Protected players
- [ ] Investigation results
- [ ] Role-specific abilities
- [ ] Death messages
- [ ] Survivor messages

**Rollback Plan:**
- Feature flag per game mode
- Test in private chats first
- Have old version ready

---

### **PHASE 6: Day Vote & Vote Likes** ☀️ (MEDIUM-HIGH)
**Duration:** 1 week
**Risk:** Medium-High

#### Functions to migrate:

1. **day_action** → `phase_service.run_day_phase()`
   - Send vote buttons
   - Track votes
   
2. **stop_voting_mafias** → Already in vote_service (partial)
   - Count mafia night votes
   - Determine kill target
   
3. **vote_like_action** → `vote_service.run_vote_like_phase()`
   - Send like/dislike buttons
   - Collect reactions
   
4. **handle_vote_like** → Callback handler
5. **check_vote_like_result** → `vote_service.check_vote_like_result()`
   - Determine if player should be executed

**Testing Checklist:**
- [ ] Day voting works
- [ ] Vote counting correct
- [ ] Mafia vote works
- [ ] Vote like/dislike
- [ ] Execution logic
- [ ] Tied votes handling

**Rollback Plan:** Feature flag

---

### **PHASE 7: Game End & Results** 🏆 (MEDIUM)
**Duration:** 1 week
**Risk:** Medium

#### Functions to migrate:

1. **announce_game_result** → `game_service.announce_results()`
   - Winner detection logic
   - Profile updates (dollar, wins, games_count)
   - PlayersGameBall updates
   - Statistics
   
2. **stop_game_handler** → `game_service.stop_game()`
   - Force stop by admin
   - Call announce_results

3. **check_paralar_lst** → Para mode logic
4. **check_mafialar_list** → Helper

**Testing Checklist:**
- [ ] Correct winner detection (all modes)
- [ ] Profile updates
- [ ] Statistics saved
- [ ] Dollar distribution
- [ ] Para mode
- [ ] VS game mode

**Rollback Plan:** Keep statistics in old format

---

### **PHASE 8: Edge Cases & Special Roles** 🎭 (MEDIUM)
**Duration:** 1-2 weeks
**Risk:** Medium

#### Functions to migrate:

1. **assign_new_role** → `role_service.reassign_role()`
   - When player dies, reassign role if needed
   - Complex logic for role replacement

**Testing:**
- [ ] All 50+ roles work correctly
- [ ] Special abilities
- [ ] Win conditions
- [ ] Role interactions

---

### **PHASE 9: Integration & Cleanup** 🧹 (LOW)
**Duration:** 1 week
**Risk:** Low

- [ ] Update all handlers to use Redis services
- [ ] Remove feature flags (if stable)
- [ ] Archive game_logic.py
- [ ] Documentation
- [ ] Performance optimization

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/redis_game/
├── test_game_service.py
├── test_player_service.py
├── test_phase_service.py
├── test_action_service.py
├── test_vote_service.py
└── test_role_service.py
```

### Integration Tests
```python
# tests/integration/
├── test_full_game_flow.py
├── test_vs_game.py
├── test_para_mode.py
└── test_all_roles.py
```

### Manual Testing
- [ ] Test with 5 players (minimum)
- [ ] Test with 15 players (maximum)
- [ ] Test each role at least once
- [ ] Test VS game modes
- [ ] Test para modes
- [ ] Test admin commands

---

## 🚨 Risk Mitigation

### High-Risk Areas:
1. **starting_game** - Main game loop
2. **view_night_results** - 1400+ lines of logic
3. **rol_taqsimlash** - Role assignment
4. **announce_game_result** - Winner detection

### Mitigation:
- Split into smaller functions
- Extensive testing
- Feature flags
- Gradual rollout (1 chat at a time)
- Keep old code running in parallel
- Monitor logs and errors
- Have rollback ready at all times

---

## 📊 Progress Tracking

### Overall Progress: 15% ✅

- [x] Phase 0: Preparation (Architecture) - 100%
- [ ] Phase 1: Simple Handlers - 50%
- [ ] Phase 2: Player List - 0%
- [ ] Phase 3: Kick Player - 0%
- [ ] Phase 4: Game Start - 0%
- [ ] Phase 5: Night Actions - 0%
- [ ] Phase 6: Day Vote - 0%
- [ ] Phase 7: Game End - 0%
- [ ] Phase 8: Edge Cases - 0%
- [ ] Phase 9: Cleanup - 0%

### Estimated Timeline:
- **Total Duration:** 3-4 months (conservative)
- **with 2-3 hours/day:** 4-5 months
- **with full-time:** 2 months

---

## 🎯 Next Immediate Steps:

1. **Create feature flags system**
   ```python
   # config.py or utils/redis_game/feature_flags.py
   REDIS_GAME_ENABLED = False
   REDIS_GAME_CHATS = []  # Whitelist
   ```

2. **Create wrapper for gradual migration**
   ```python
   # handlers/game.py
   async def create_game(message, bot):
       if REDIS_GAME_ENABLED and message.chat.id in REDIS_GAME_CHATS:
           from utils.redis_game import game_service
           return await game_service.create_game(message, bot)
       else:
           from utils.game_logic import create_game_handler
           return await create_game_handler(message, bot)
   ```

3. **Start with Phase 1 testing**

---

## 🔗 Dependencies to Preserve

Must work with existing:
- ✅ Tortoise ORM (for statistics)
- ✅ Aiogram handlers
- ✅ Keyboards
- ✅ User/Profile models
- ✅ GameSet models
- ✅ Geroy handlers

---

## ⚠️ CRITICAL: What NOT to Break

1. Existing active games (don't break mid-game!)
2. User profiles and statistics
3. Dollar/diamond economy
4. Active roles
5. Weapons inventory
6. Geroy game integration
7. Para system
8. VS game system

---

**Last Updated:** 2025-12-17
**Next Review:** After Phase 1 completion
