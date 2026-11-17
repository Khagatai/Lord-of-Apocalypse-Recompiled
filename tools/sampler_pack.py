"""Host replacement keys for independently restored clamp/repeat contexts."""
import re

NAMESPACE={'version':1,'data_xor_base':'4c4f4100','wrap_bits':'s0-t8'}


def validate(value):
    if value is not None and value!=NAMESPACE:
        raise ValueError('Unsupported sampler replacement namespace')
    return value


def tagged_key(key,wrap):
    if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{24}',key):
        raise ValueError('Invalid original texture identity')
    if type(wrap) is not int or wrap not in (0,1,256,257):
        raise ValueError('Invalid sampler context')
    tag=0x4c4f4100|(wrap&1)|((wrap>>7)&2)
    data_hash=int(key[16:],16)^tag
    if not data_hash:raise ValueError('Sampler tag would create a wildcard data hash')
    return key[:16]+f'{data_hash:08x}'


def require_runtime(namespace,metadata,executable_sha256):
    if not validate(namespace):return
    renderer=metadata.get('renderer') or metadata.get('source_patch') or {}
    built=metadata.get('executable_sha256') or metadata.get('prototype_executable_sha256')
    if renderer.get('sampler_namespace_version')!=1 or built!=executable_sha256:
        raise ValueError('Sampler-aware texture pack requires a matching rebuilt renderer')
