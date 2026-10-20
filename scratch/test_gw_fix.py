import sys, types, asyncio

sys.path.insert(0, r'd:\Empire_Turon_maf_Bot\Empire_bot_toliq\Empire')
print('step0: path set', flush=True)

import fakeredis
fake = fakeredis.FakeAsyncRedis(decode_responses=True)
print('step1: fakeredis ok', flush=True)

utils_pkg = types.ModuleType('utils')
utils_pkg.__path__ = [r'd:\Empire_Turon_maf_Bot\Empire_bot_toliq\Empire\utils']
db_stub = types.ModuleType('utils.database')
db_stub.redis_client = fake
sys.modules['utils'] = utils_pkg
sys.modules['utils.database'] = db_stub
print('step2: stubs installed', flush=True)

import utils.giveaways_redis as gr
gr.redis_client = fake  # bind explicitly
print('step3: giveaways_redis imported', flush=True)


async def main():
    gw = await gr.create_giveaway(creator_id=1, chat_id=-100, message_id=5, total_amount=10)
    assert gw and gw['id'] == 1, gw
    got = await gr.get_giveaway(1)
    assert got['remaining_amount'] == 10 and got['total_amount'] == 10, got
    print('step4: create/get ok', flush=True)

    assert await gr.update_giveaway(1, {'remaining_amount': 9}) is True
    got2 = await gr.get_giveaway(1)
    assert got2['remaining_amount'] == 9, got2
    print('step5: update ok', flush=True)

    await fake.hset('giveaway:99', mapping={'id': '99'})
    assert await gr.get_giveaway(99) is None
    print('step6: partial hash ok', flush=True)

    assert await gr.mark_as_processing(1, 42) is True
    assert await gr.is_processing(1, 42) is True
    await gr.unmark_as_processing(1, 42)
    assert await gr.is_processing(1, 42) is False
    print('step7: lock ok', flush=True)

    await gr.queue_collected_user(1, 42)
    await gr.queue_winner_detail(1, 42, 'Test User', 1)
    await gr.flush_all_giveaway_buffers(1)
    users = await gr.get_collected_users(1)
    assert 42 in users, users
    wins = await gr.get_winner_details(1)
    assert wins and wins[0][0] == 42, wins
    assert await gr.is_collected_user(1, 42) is True
    print('step8: buffers ok', flush=True)

    data = 'money-giveaway_7_100_10'
    parts = data.split('_')
    gid, rem, per = parts[1], int(parts[2]), int(parts[3])
    assert (gid, rem, per) == ('7', 100, 10), (gid, rem, per)

    dparts = 'giveaway_12_10_10'.split('_')
    assert (dparts[1], int(dparts[2]), int(dparts[3])) == ('12', 10, 10)
    cparts = 'channel-giveaway_5_11_11'.split('_')
    assert (cparts[1], int(cparts[2]), int(cparts[3])) == ('5', 11, 11)

    print('ALL TESTS PASSED')


asyncio.run(main())
