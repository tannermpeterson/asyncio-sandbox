import asyncio
import aiomultiprocess
from queue import Empty


async def handle_user_input(subprocess_input_queue):
    while True:
        user_input = input("enter: ")
        if user_input == "quit":
            subprocess_input_queue.put_nowait({"command": "quit"})
            return
        elif user_input == "tanner":
            subprocess_input_queue.put_nowait({"command": "tanner"})
        elif user_input == "start timer":
            dur = input("how long?: ")
            try:
                parsed_dur = int(dur)
            except:
                print("invalid value")
            else:
                subprocess_input_queue.put_nowait({"command": "start_timer", "dur": parsed_dur})
        else:
            print("ignoring input")


async def timer(time_remaining):
    while time_remaining > 0:
        print(time_remaining)
        await asyncio.sleep(1)
        time_remaining -= 1
    print("TIMER COMPLETE")


async def handle_command(input_queue):
    tasks = set()

    command_dict = None
    while command_dict is None:
        try:
            command_dict = input_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)
    command = command_dict["command"]
    if command == "quit":
        return set()
    elif command == "tanner":
        print("that's my name")
    elif command == "start_timer":
        tasks.add(asyncio.create_task(timer(command_dict["dur"])))
    else:
        print(f"unrecognized command: {command}")

    tasks.add(asyncio.create_task(handle_command(input_queue)))
    return tasks


async def subprocess_main(input_queue):
    pending = {asyncio.create_task(handle_command(input_queue))}
    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for coro in done:
            coro_result = coro.result()
            if coro_result is None:
                continue
            for task in coro_result:
                pending.add(task)
        if not pending:
            print("subprocess quitting")
            return


async def main():
    subprocess_input_queue = aiomultiprocess.core.get_manager().Queue()
    async_process = aiomultiprocess.Process(target=subprocess_main, args=(subprocess_input_queue,))
    async_process.start()
    await asyncio.gather(handle_user_input(subprocess_input_queue), async_process.join())


if __name__ == "__main__":
    aiomultiprocess.set_start_method("spawn")
    asyncio.run(main())
