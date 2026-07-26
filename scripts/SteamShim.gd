extends Node
## No-op Steam shim for the iOS 1:1 port.
##
## The original game targets the GodotSteam GDExtension (the `Steam` singleton),
## which does not exist on stock iOS export templates. This autoload is
## registered under the name `Steam` so every `Steam.xxx()` call, constant and
## signal in the codebase resolves and does nothing — letting the full original
## project run on iOS. Singleplayer (campaign + endless) is unaffected; only
## online multiplayer and Steam achievements/leaderboards become inert.

# ── Signals the game connects to (must exist so `.connect()` parses) ──
signal lobby_created(_a, _b)
signal lobby_joined(_a, _b, _c, _d)
signal lobby_match_list(_a)
signal lobby_chat_update(_a, _b, _c, _d)
signal join_requested(_a, _b)
signal persona_state_change(_a, _b)
signal avatar_loaded(_a, _b, _c)
signal leaderboard_find_result(_a, _b)
signal leaderboard_score_uploaded(_a, _b, _c)
signal leaderboard_scores_downloaded(_a, _b, _c)

# ── Constants referenced across the codebase ──
const PACKET_READ_LIMIT: int = 32
const LOBBY_TYPE_PUBLIC = 2
const LOBBY_TYPE_FRIENDS_ONLY = 1
const LOBBY_DISTANCE_FILTER_WORLDWIDE = 3
const LOBBY_DISTANCE_FILTER_FAR = 2
const LOBBY_DISTANCE_FILTER_CLOSE = 1
const LEADERBOARD_DATA_REQUEST_GLOBAL = 0
const LEADERBOARD_DATA_REQUEST_GLOBAL_AROUND_USER = 1
const LEADERBOARD_DATA_REQUEST_FRIENDS = 2
const CHAT_ROOM_ENTER_RESPONSE_SUCCESS = 1
const CHAT_ROOM_ENTER_RESPONSE_DOESNT_EXIST = 2
const CHAT_ROOM_ENTER_RESPONSE_NOT_ALLOWED = 3
const CHAT_ROOM_ENTER_RESPONSE_FULL = 4
const CHAT_ROOM_ENTER_RESPONSE_ERROR = 5
const CHAT_ROOM_ENTER_RESPONSE_BANNED = 6
const CHAT_ROOM_ENTER_RESPONSE_LIMITED = 7
const CHAT_ROOM_ENTER_RESPONSE_CLAN_DISABLED = 8
const CHAT_ROOM_ENTER_RESPONSE_COMMUNITY_BAN = 9
const CHAT_ROOM_ENTER_RESPONSE_MEMBER_BLOCKED_YOU = 10
const CHAT_ROOM_ENTER_RESPONSE_YOU_BLOCKED_MEMBER = 11
const CHAT_MEMBER_STATE_CHANGE_ENTERED = 1
const CHAT_MEMBER_STATE_CHANGE_LEFT = 2
const CHAT_MEMBER_STATE_CHANGE_KICKED = 8
const CHAT_MEMBER_STATE_CHANGE_BANNED = 16

func _ready() -> void:
	print("Steam shim active (no Steam on iOS) — singleplayer only")

func _process(_delta: float) -> void:
	pass

# ── Init / session ──
func steamInit(_a = false) -> Dictionary: return {"status": 0, "verbal": "shim"}
func run_callbacks() -> void: pass
func loggedOn() -> bool: return false
func getSteamID() -> int: return 0
func getPersonaName() -> String: return "Player"
func getFriendPersonaName(_id) -> String: return "Player"
func isSteamRunningOnSteamDeck() -> bool: return false

# ── Stats / achievements / leaderboards (inert) ──
func setAchievement(_name) -> bool: return false
func clearAchievement(_name) -> bool: return false
func storeStats() -> bool: return false
func findLeaderboard(_name) -> void: pass
func getLeaderboardEntryCount(_handle = 0) -> int: return 0
func setLeaderboardDetailsMax(_n) -> int: return 0
func uploadLeaderboardScore(_score, _keep = true, _details = PackedInt32Array(), _handle = 0) -> void: pass
func downloadLeaderboardEntries(_start, _end, _type = 0) -> void: pass

# ── Lobby / matchmaking (inert on iOS) ──
func createLobby(_type = 0, _max = 4) -> void: pass
func joinLobby(_id) -> void: pass
func leaveLobby(_id) -> void: pass
func getLobbyData(_id, _key) -> String: return ""
func setLobbyData(_id, _key, _value) -> bool: return false
func setLobbyJoinable(_id, _joinable) -> bool: return false
func setLobbyType(_id, _type) -> bool: return false
func setLobbyMemberLimit(_id, _limit) -> bool: return false
func getLobbyOwner(_id) -> int: return 0
func getNumLobbyMembers(_id) -> int: return 0
func getLobbyMemberByIndex(_id, _index) -> int: return 0
func requestLobbyList() -> void: pass
func addRequestLobbyListDistanceFilter(_f) -> void: pass
func addRequestLobbyListResultCountFilter(_n) -> void: pass
func activateGameOverlayInviteDialog(_id) -> void: pass

# ── Friends / avatars ──
func getPlayerAvatar(_size = 2, _id = 0) -> void: pass

# ── Networking packets (inert) ──
func sendP2PPacket(_a = 0, _b = null, _c = 0, _d = 0) -> bool: return false
func getAvailableP2PPacketSize(_channel = 0) -> int: return 0
func readP2PPacket(_size = 0, _channel = 0) -> Dictionary: return {}
func acceptP2PSessionWithUser(_id) -> bool: return false
func allowP2PPacketRelay(_allow) -> bool: return false
func closeP2PSessionWithUser(_id) -> bool: return false
