"""Switch between the room service and optional Steam development backend via F1."""
from online_agent import Agent,BAD,OK
import online_config
class Router:
    def __init__(self,identity,service='',*,backend='rooms',relay=False,preferences=None):
        self.identity=identity;self.service=service;self.relay=relay;self.preferences=preferences;self.backend=backend;self.agent=self.make(backend)
    def make(self,backend):
        if backend=='steam':
            from steam_agent import SteamAgent
            return SteamAgent(self.identity)
        return Agent(self.identity,self.service,relay=self.relay)
    @property
    def closed(self):return self.agent.closed
    def tick(self):return self.agent.tick()
    def request(self,body):
        if body.get('op')=='backend':
            backend=body.get('backend')
            if backend not in ('rooms','steam'):return dict(result=BAD,error='Unknown networking provider.')
            if self.agent.room or self.agent.state in ('creating','joining'):return dict(result=BAD,error='Leave the current room before changing provider.')
            if backend!=self.backend or (backend=='steam' and self.agent.steam is None):
                candidate=self.make(backend)
                try:
                    if self.preferences:online_config.save(dict(backend=backend,url=self.service),self.preferences)
                except BaseException:candidate.close();raise
                self.agent.close();self.agent=candidate;self.backend=backend
            return dict(result=OK)
        value=self.agent.request(body)
        if body.get('op')=='status':value['backend']=self.backend
        return value
    def close(self):self.agent.close()
