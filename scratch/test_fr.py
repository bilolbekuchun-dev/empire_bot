import fakeredis
import asyncio

print('import ok')

async def t():
    f = fakeredis.FakeAsyncRedis(decode_responses=True)
    print('ping', await f.ping())
    await f.hset('k', mapping={'a': '1', 'b': '2'})
    print('hgetall', await f.hgetall('k'))
    print('incr', await f.incr('c'))
    r = await f.set('lk', '1', nx=True, ex=30)
    print('set nx', r)
    print('set nx again', await f.set('lk', '1', nx=True, ex=30))

asyncio.run(t())
print('FAKEREDIS TEST DONE')
