/* SPDX-License-Identifier: MIT
 * Original forwarding helpers. All SDK calls cross Valve's flat C ABI rather
 * than invoking MSVC C++ vtables from MinGW (CSteamID returns differ). */
#include <steam/steam_api_flat.h>
struct FlatMatchmaking {
    ISteamMatchmaking *self() const {return SteamAPI_SteamMatchmaking();}
    const char *GetLobbyData(CSteamID id,const char *key) {return SteamAPI_ISteamMatchmaking_GetLobbyData(self(),id.ConvertToUint64(),key);}
    int GetNumLobbyMembers(CSteamID id) {return SteamAPI_ISteamMatchmaking_GetNumLobbyMembers(self(),id.ConvertToUint64());}
    CSteamID GetLobbyMemberByIndex(CSteamID id,int index) {return CSteamID(SteamAPI_ISteamMatchmaking_GetLobbyMemberByIndex(self(),id.ConvertToUint64(),index));}
    CSteamID GetLobbyOwner(CSteamID id) {return CSteamID(SteamAPI_ISteamMatchmaking_GetLobbyOwner(self(),id.ConvertToUint64()));}
    int GetLobbyMemberLimit(CSteamID id) {return SteamAPI_ISteamMatchmaking_GetLobbyMemberLimit(self(),id.ConvertToUint64());}
    void LeaveLobby(CSteamID id) {SteamAPI_ISteamMatchmaking_LeaveLobby(self(),id.ConvertToUint64());}
    bool SetLobbyJoinable(CSteamID id,bool enabled) {return SteamAPI_ISteamMatchmaking_SetLobbyJoinable(self(),id.ConvertToUint64(),enabled);}
    bool SetLobbyData(CSteamID id,const char *key,const char *value) {return SteamAPI_ISteamMatchmaking_SetLobbyData(self(),id.ConvertToUint64(),key,value);}
    bool SetLobbyMemberLimit(CSteamID id,int limit) {return SteamAPI_ISteamMatchmaking_SetLobbyMemberLimit(self(),id.ConvertToUint64(),limit);}
    void SetLobbyMemberData(CSteamID id,const char *key,const char *value) {SteamAPI_ISteamMatchmaking_SetLobbyMemberData(self(),id.ConvertToUint64(),key,value);}
    const char *GetLobbyMemberData(CSteamID id,CSteamID member,const char *key) {return SteamAPI_ISteamMatchmaking_GetLobbyMemberData(self(),id.ConvertToUint64(),member.ConvertToUint64(),key);}
    bool RequestLobbyData(CSteamID id) {return SteamAPI_ISteamMatchmaking_RequestLobbyData(self(),id.ConvertToUint64());}
    SteamAPICall_t JoinLobby(CSteamID id) {return SteamAPI_ISteamMatchmaking_JoinLobby(self(),id.ConvertToUint64());}
    SteamAPICall_t CreateLobby(ELobbyType type,int count) {return SteamAPI_ISteamMatchmaking_CreateLobby(self(),type,count);}
};
struct FlatFriends {
    ISteamFriends *self() const {return SteamAPI_SteamFriends();}
    const char *GetPersonaName() {return SteamAPI_ISteamFriends_GetPersonaName(self());}
    const char *GetFriendPersonaName(CSteamID id) {return SteamAPI_ISteamFriends_GetFriendPersonaName(self(),id.ConvertToUint64());}
    int GetFriendCount(int flags) {return SteamAPI_ISteamFriends_GetFriendCount(self(),flags);}
    CSteamID GetFriendByIndex(int i,int flags) {return CSteamID(SteamAPI_ISteamFriends_GetFriendByIndex(self(),i,flags));}
    bool GetFriendGamePlayed(CSteamID id,FriendGameInfo_t *info) {return SteamAPI_ISteamFriends_GetFriendGamePlayed(self(),id.ConvertToUint64(),info);}
    bool HasFriend(CSteamID id,int flags) {return SteamAPI_ISteamFriends_HasFriend(self(),id.ConvertToUint64(),flags);}
    void ActivateGameOverlayInviteDialog(CSteamID id) {SteamAPI_ISteamFriends_ActivateGameOverlayInviteDialog(self(),id.ConvertToUint64());}
};
struct FlatUser {
    CSteamID GetSteamID() {return CSteamID(SteamAPI_ISteamUser_GetSteamID(SteamAPI_SteamUser()));}
    bool BLoggedOn() {return SteamAPI_ISteamUser_BLoggedOn(SteamAPI_SteamUser());}
};
struct FlatUtils {
    AppId_t GetAppID() {return SteamAPI_ISteamUtils_GetAppID(SteamAPI_SteamUtils());}
    bool IsOverlayEnabled() {return SteamAPI_ISteamUtils_IsOverlayEnabled(SteamAPI_SteamUtils());}
};
struct FlatMessages {
    ISteamNetworkingMessages *self() const {return SteamAPI_SteamNetworkingMessages_SteamAPI();}
    bool AcceptSessionWithUser(const SteamNetworkingIdentity &id) {return SteamAPI_ISteamNetworkingMessages_AcceptSessionWithUser(self(),id);}
    bool CloseSessionWithUser(const SteamNetworkingIdentity &id) {return SteamAPI_ISteamNetworkingMessages_CloseSessionWithUser(self(),id);}
    EResult SendMessageToUser(const SteamNetworkingIdentity &id,const void *data,uint32_t size,int flags,int channel) {return SteamAPI_ISteamNetworkingMessages_SendMessageToUser(self(),id,data,size,flags,channel);}
    int ReceiveMessagesOnChannel(int channel,SteamNetworkingMessage_t **messages,int max) {return SteamAPI_ISteamNetworkingMessages_ReceiveMessagesOnChannel(self(),channel,messages,max);}
    ESteamNetworkingConnectionState GetSessionConnectionInfo(const SteamNetworkingIdentity &id,SteamNetConnectionInfo_t *info,SteamNetConnectionRealTimeStatus_t *status) {return SteamAPI_ISteamNetworkingMessages_GetSessionConnectionInfo(self(),id,info,status);}
};
struct FlatNetworkUtils {void InitRelayNetworkAccess() {SteamAPI_ISteamNetworkingUtils_InitRelayNetworkAccess(SteamAPI_SteamNetworkingUtils_SteamAPI());}};
static FlatMatchmaking flat_matchmaking;
static FlatFriends flat_friends;
static FlatUser flat_user;
static FlatUtils flat_utils;
static FlatMessages flat_messages;
static FlatNetworkUtils flat_network_utils;
#define SteamMatchmaking() (&flat_matchmaking)
#define SteamFriends() (&flat_friends)
#define SteamUser() (&flat_user)
#define SteamUtils() (&flat_utils)
#define SteamNetworkingMessages() (&flat_messages)
#define SteamNetworkingUtils() (&flat_network_utils)
