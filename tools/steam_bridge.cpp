/* SPDX-License-Identifier: MIT
 * Original standalone Steamworks adapter. Compiles only against a user-supplied
 * official SDK. No SDK headers, redistributables or game content are included.
 * Run only in the owned online helper, not linked into the recomp executable. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <steam/steam_api.h>
#include <steam/isteamnetworkingmessages.h>
#include <steam/isteamnetworkingutils.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "steam_flat.h"
#define API extern "C" __declspec(dllexport)
static constexpr const char *project="loa-recomp-npjh50503-steam-test-v1";
static constexpr const char *project_key="loa_recomp_protocol";
static constexpr int channel_reliable=31470,channel_datagram=31471;
struct Status {uint64_t user,lobby,owner;int32_t state,players,overlay;char name[128],error[256];};
struct Member {uint64_t user;char name[128],mac[18];};
struct Room {uint64_t lobby,owner;int32_t players;char name[128];};
class Bridge {
public:
    CSteamID lobby,requested,initial_owner;
    int state=0;
    ULONGLONG deadline=0,last_refresh=0;
    char error[256]={0},mac[18]={0};
    SteamAPICall_t created=0,entered=0;
    std::vector<uint64_t> candidates;
    bool compatible(CSteamID id) const {return !strcmp(SteamMatchmaking()->GetLobbyData(id,project_key),project);}
    bool member(CSteamID id) const {
        if(!lobby.IsValid() || !compatible(lobby))return false;
        int n=SteamMatchmaking()->GetNumLobbyMembers(lobby);
        if(n<1 || n>4)return false;
        for(int i=0;i<n;i++)if(SteamMatchmaking()->GetLobbyMemberByIndex(lobby,i)==id)return true;
        return false;
    }
    void fail(const char *text) {snprintf(error,sizeof error,"%s",text);state=-1;deadline=0;requested=CSteamID();}
    void leave() {
        if(lobby.IsValid()) {
            int n=SteamMatchmaking()->GetNumLobbyMembers(lobby);
            for(int i=0;i<n;i++) {
                SteamNetworkingIdentity id;id.SetSteamID(SteamMatchmaking()->GetLobbyMemberByIndex(lobby,i));
                SteamNetworkingMessages()->CloseSessionWithUser(id);
            }
            SteamMatchmaking()->LeaveLobby(lobby);
        }
        lobby=CSteamID();requested=CSteamID();initial_owner=CSteamID();state=0;deadline=0;
    }
    void on_created(LobbyCreated_t *result,bool io) {
        if(state!=1) {if(!io && result->m_eResult==k_EResultOK)SteamMatchmaking()->LeaveLobby(CSteamID(result->m_ulSteamIDLobby));return;}
        if(io || result->m_eResult!=k_EResultOK) {fail("Steam could not create the test lobby.");return;}
        lobby=CSteamID(result->m_ulSteamIDLobby);
        bool ok=SteamMatchmaking()->SetLobbyJoinable(lobby,false);
        ok=SteamMatchmaking()->SetLobbyData(lobby,project_key,project)&&ok;
        ok=SteamMatchmaking()->SetLobbyData(lobby,"name","Lord of Apocalypse - development test")&&ok;
        ok=SteamMatchmaking()->SetLobbyMemberLimit(lobby,4)&&ok;
        SteamMatchmaking()->SetLobbyMemberData(lobby,"loa_mac",mac);
        if(!ok || !SteamMatchmaking()->SetLobbyJoinable(lobby,true)) {leave();fail("Steam lobby setup failed.");return;}
        initial_owner=SteamUser()->GetSteamID();state=3;deadline=0;
    }
    bool join(CSteamID id) {
        if(lobby.IsValid() || state==1 || state==2 || !id.IsValid())return false;
        error[0]=0;requested=id;state=2;deadline=GetTickCount64()+30000;
        if(!SteamMatchmaking()->RequestLobbyData(id)) {fail("Cannot read this Steam lobby.");return false;}
        return true;
    }
    void begin_enter() {
        if(!compatible(requested)) {fail("This lobby is not a compatible Lord of Apocalypse test room.");return;}
        if(SteamMatchmaking()->GetLobbyMemberLimit(requested)!=4) {fail("Incompatible lobby capacity.");return;}
        SteamAPICall_t call=SteamMatchmaking()->JoinLobby(requested);
        if(call==k_uAPICallInvalid) {fail("Steam refused the lobby join request.");return;}
        entered=call;requested=CSteamID();
    }
    void on_entered(LobbyEnter_t *result,bool io) {
        CSteamID id(result->m_ulSteamIDLobby);
        if(state!=2) {if(!io)SteamMatchmaking()->LeaveLobby(id);return;}
        if(io || result->m_EChatRoomEnterResponse!=k_EChatRoomEnterResponseSuccess) {fail("Steam lobby join failed or the room is full.");return;}
        if(!compatible(id)) {SteamMatchmaking()->LeaveLobby(id);fail("Incompatible Steam test room.");return;}
        lobby=id;initial_owner=SteamMatchmaking()->GetLobbyOwner(id);
        SteamMatchmaking()->SetLobbyMemberData(lobby,"loa_mac",mac);state=3;deadline=0;
    }
    void on_lobby_data(LobbyDataUpdate_t *);
    void on_invite(GameLobbyJoinRequested_t *);
    void on_session(SteamNetworkingMessagesSessionRequest_t *);
    void on_session_failed(SteamNetworkingMessagesSessionFailed_t *);
};
void Bridge::on_lobby_data(LobbyDataUpdate_t *event) {
    if(state==2 && requested.IsValid() && event->m_ulSteamIDLobby==requested.ConvertToUint64()) {
        if(event->m_bSuccess)begin_enter();else fail("Steam could not read the invited room.");
    }
}
void Bridge::on_invite(GameLobbyJoinRequested_t *event) {
    if(!lobby.IsValid() && state!=1 && state!=2)join(event->m_steamIDLobby);
}
void Bridge::on_session(SteamNetworkingMessagesSessionRequest_t *event) {
    if(member(event->m_identityRemote.GetSteamID()))SteamNetworkingMessages()->AcceptSessionWithUser(event->m_identityRemote);
    else SteamNetworkingMessages()->CloseSessionWithUser(event->m_identityRemote);
}
void Bridge::on_session_failed(SteamNetworkingMessagesSessionFailed_t *event) {
    if(member(event->m_info.m_identityRemote.GetSteamID()))snprintf(error,sizeof error,"Steam peer connection failed (reason %d).",event->m_info.m_eEndReason);
}
static Bridge *bridge;
API int loa_steam_init(const char *mac,char *error,uint32_t capacity) {
    if(bridge)return 1;
    if(!SteamAPI_Init()) {snprintf(error,capacity,"Steam initialization failed. Start Steam, sign in, and check access to test App ID 480.");return 0;}
    if(!SteamAPI_SteamUser() || !SteamAPI_SteamUtils() || !SteamAPI_SteamMatchmaking() || !SteamAPI_SteamNetworkingMessages_SteamAPI() || !SteamUser()->BLoggedOn() || SteamUtils()->GetAppID()!=480) {
        SteamAPI_Shutdown();snprintf(error,capacity,"Steam must be online under test App ID 480.");return 0;
    }
    SteamAPI_ManualDispatch_Init();bridge=new Bridge();snprintf(bridge->mac,sizeof bridge->mac,"%s",mac);
    SteamNetworkingUtils()->InitRelayNetworkAccess();return 1;
}
API void loa_steam_tick() {
    if(!bridge)return;
    HSteamPipe pipe=SteamAPI_GetHSteamPipe();SteamAPI_ManualDispatch_RunFrame(pipe);CallbackMsg_t callback;
    for(int handled=0;handled<128 && SteamAPI_ManualDispatch_GetNextCallback(pipe,&callback);handled++) {
        if(callback.m_iCallback==SteamAPICallCompleted_t::k_iCallback && callback.m_cubParam==sizeof(SteamAPICallCompleted_t)) {
            auto *done=reinterpret_cast<SteamAPICallCompleted_t *>(callback.m_pubParam);bool failed=false;
            if(done->m_hAsyncCall==bridge->created && done->m_iCallback==LobbyCreated_t::k_iCallback) {
                LobbyCreated_t value={};bridge->created=0;
                bool ok=SteamAPI_ManualDispatch_GetAPICallResult(pipe,done->m_hAsyncCall,&value,sizeof value,LobbyCreated_t::k_iCallback,&failed);bridge->on_created(&value,!ok||failed);
            } else if(done->m_hAsyncCall==bridge->entered && done->m_iCallback==LobbyEnter_t::k_iCallback) {
                LobbyEnter_t value={};bridge->entered=0;
                bool ok=SteamAPI_ManualDispatch_GetAPICallResult(pipe,done->m_hAsyncCall,&value,sizeof value,LobbyEnter_t::k_iCallback,&failed);bridge->on_entered(&value,!ok||failed);
            }
        } else if(callback.m_iCallback==LobbyDataUpdate_t::k_iCallback && callback.m_cubParam==sizeof(LobbyDataUpdate_t))bridge->on_lobby_data(reinterpret_cast<LobbyDataUpdate_t *>(callback.m_pubParam));
        else if(callback.m_iCallback==GameLobbyJoinRequested_t::k_iCallback && callback.m_cubParam==sizeof(GameLobbyJoinRequested_t))bridge->on_invite(reinterpret_cast<GameLobbyJoinRequested_t *>(callback.m_pubParam));
        else if(callback.m_iCallback==SteamNetworkingMessagesSessionRequest_t::k_iCallback && callback.m_cubParam==sizeof(SteamNetworkingMessagesSessionRequest_t))bridge->on_session(reinterpret_cast<SteamNetworkingMessagesSessionRequest_t *>(callback.m_pubParam));
        else if(callback.m_iCallback==SteamNetworkingMessagesSessionFailed_t::k_iCallback && callback.m_cubParam==sizeof(SteamNetworkingMessagesSessionFailed_t))bridge->on_session_failed(reinterpret_cast<SteamNetworkingMessagesSessionFailed_t *>(callback.m_pubParam));
        SteamAPI_ManualDispatch_FreeLastCallback(pipe);
    }
    if(bridge->deadline && GetTickCount64()>bridge->deadline) {
        bridge->leave();bridge->fail("Steam lobby request timed out.");
    }
    if(bridge->lobby.IsValid() && SteamMatchmaking()->GetLobbyOwner(bridge->lobby)!=bridge->initial_owner) {
        bridge->leave();bridge->fail("The host left the Steam lobby. Create or join another room.");
    }
}
API int loa_steam_status(Status *out) {
    if(!bridge || !out)return 0;
    memset(out,0,sizeof *out);out->user=SteamUser()->GetSteamID().ConvertToUint64();out->lobby=bridge->lobby.ConvertToUint64();
    out->owner=bridge->initial_owner.ConvertToUint64();out->state=bridge->state;
    out->players=bridge->lobby.IsValid()?SteamMatchmaking()->GetNumLobbyMembers(bridge->lobby):0;
    out->overlay=SteamUtils()->IsOverlayEnabled()?1:0;
    snprintf(out->name,sizeof out->name,"%s",SteamFriends()->GetPersonaName());snprintf(out->error,sizeof out->error,"%s",bridge->error);return 1;
}
API int loa_steam_create() {
    if(!bridge || bridge->lobby.IsValid() || bridge->state==1 || bridge->state==2)return 0;
    bridge->error[0]=0;bridge->state=1;bridge->deadline=GetTickCount64()+30000;
    SteamAPICall_t call=SteamMatchmaking()->CreateLobby(k_ELobbyTypeFriendsOnly,4);
    if(call==k_uAPICallInvalid) {bridge->fail("Steam rejected lobby creation.");return 0;}
    bridge->created=call;return 1;
}
API int loa_steam_join(uint64_t lobby) {return bridge && bridge->join(CSteamID(lobby));}
API void loa_steam_leave() {if(bridge)bridge->leave();}
API int loa_steam_members(Member *out,int capacity) {
    if(!bridge || !bridge->lobby.IsValid() || !out || capacity<0)return 0;
    int n=SteamMatchmaking()->GetNumLobbyMembers(bridge->lobby),count=0;
    for(int i=0;i<n && count<capacity && count<4;i++) {
        CSteamID id=SteamMatchmaking()->GetLobbyMemberByIndex(bridge->lobby,i);Member row={};row.user=id.ConvertToUint64();
        snprintf(row.name,sizeof row.name,"%s",SteamFriends()->GetFriendPersonaName(id));
        snprintf(row.mac,sizeof row.mac,"%s",SteamMatchmaking()->GetLobbyMemberData(bridge->lobby,id,"loa_mac"));out[count++]=row;
    }
    return count;
}
API void loa_steam_refresh() {
    if(!bridge || GetTickCount64()-bridge->last_refresh<3000)return;
    bridge->last_refresh=GetTickCount64();bridge->candidates.clear();
    int n=SteamFriends()->GetFriendCount(k_EFriendFlagImmediate);
    for(int i=0;i<n && bridge->candidates.size()<64;i++) {
        FriendGameInfo_t info={};CSteamID user=SteamFriends()->GetFriendByIndex(i,k_EFriendFlagImmediate);
        if(!SteamFriends()->GetFriendGamePlayed(user,&info) || info.m_gameID.AppID()!=480 || !info.m_steamIDLobby.IsValid())continue;
        uint64_t lobby=info.m_steamIDLobby.ConvertToUint64();
        if(std::find(bridge->candidates.begin(),bridge->candidates.end(),lobby)!=bridge->candidates.end())continue;
        bridge->candidates.push_back(lobby);SteamMatchmaking()->RequestLobbyData(info.m_steamIDLobby);
    }
}
API int loa_steam_rooms(Room *out,int capacity) {
    if(!bridge || !out || capacity<0)return 0;
    int count=0;
    for(uint64_t value:bridge->candidates) {
        if(count>=capacity)break;
        CSteamID id(value);
        if(!bridge->compatible(id) || SteamMatchmaking()->GetLobbyMemberLimit(id)!=4)continue;
        CSteamID owner=SteamMatchmaking()->GetLobbyOwner(id);
        if(!SteamFriends()->HasFriend(owner,k_EFriendFlagImmediate))continue;
        Room row={};row.lobby=value;row.owner=owner.ConvertToUint64();row.players=SteamMatchmaking()->GetNumLobbyMembers(id);
        snprintf(row.name,sizeof row.name,"%s",SteamFriends()->GetFriendPersonaName(owner));out[count++]=row;
    }
    return count;
}
API int loa_steam_invite() {
    if(!bridge || !bridge->lobby.IsValid() || !SteamUtils()->IsOverlayEnabled())return 0;
    SteamFriends()->ActivateGameOverlayInviteDialog(bridge->lobby);return 1;
}
API int loa_steam_send(uint64_t peer,const void *data,uint32_t size,int unreliable) {
    if(!bridge || !data || size==0 || size>17000 || !bridge->member(CSteamID(peer)))return -1;
    SteamNetworkingIdentity id;id.SetSteamID64(peer);
    int flags=unreliable?k_nSteamNetworkingSend_UnreliableNoNagle:(k_nSteamNetworkingSend_Reliable|k_nSteamNetworkingSend_NoNagle);
    EResult result=SteamNetworkingMessages()->SendMessageToUser(id,data,size,flags,unreliable?channel_datagram:channel_reliable);
    return result==k_EResultOK?0:-static_cast<int>(result);
}
API int loa_steam_receive(uint64_t *peer,void *data,uint32_t capacity,int *channel) {
    if(!bridge || !peer || !data || !channel)return -1;
    for(int index=0;index<2;index++) {
        SteamNetworkingMessage_t *message=nullptr;
        if(SteamNetworkingMessages()->ReceiveMessagesOnChannel(index?channel_datagram:channel_reliable,&message,1)<=0)continue;
        int size=message->m_cbSize;
        bool valid=bridge->member(message->m_identityPeer.GetSteamID()) && size>0 && static_cast<uint32_t>(size)<=capacity;
        if(valid) {*peer=message->m_identityPeer.GetSteamID64();*channel=index;memcpy(data,message->m_pData,static_cast<size_t>(size));}
        message->Release();if(valid)return size;
    }
    return 0;
}
API int loa_steam_connected(uint64_t peer) {
    if(!bridge || !bridge->member(CSteamID(peer)))return 0;
    SteamNetworkingIdentity id;id.SetSteamID64(peer);SteamNetConnectionInfo_t info={};
    return SteamNetworkingMessages()->GetSessionConnectionInfo(id,&info,nullptr)==k_ESteamNetworkingConnectionState_Connected;
}
API void loa_steam_close_peer(uint64_t peer) {
    if(bridge) {SteamNetworkingIdentity id;id.SetSteamID64(peer);SteamNetworkingMessages()->CloseSessionWithUser(id);}
}
API void loa_steam_shutdown() {if(bridge){bridge->leave();delete bridge;bridge=nullptr;SteamAPI_Shutdown();}}
