import asyncio
import aiomultiprocess
from queue import Empty


async def handle_user_input(subprocess_input_queue):
    """Wait for user input and queue a command if applicable.

    Entering 'quit' will break the loop and enqueue the tombstone message.
    """
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
    """Start a countdown timer with the given number of seconds"""
    while time_remaining > 0:
        print(time_remaining)
        await asyncio.sleep(1)
        time_remaining -= 1
    print("TIMER COMPLETE")


async def handle_command(input_queue):
    """Wait for a command in the queue and then process it.

    Returns new tasks which should be awaited together.
    Includes itself in tasks unless quitting so that the next
    command can be processed.
    """
    tasks = set()

    # Regular mp queue is not awaitable and thus will block, so need to poll it then
    # sleep to prevent blocking other coroutines. Should replace this with a
    # process/thread safe + asyncio compatible queue
    command_dict = None
    while not command_dict:
        try:
            command_dict = input_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.01)

    # process command
    command = command_dict["command"]
    if command == "quit":
        return set()
    elif command == "tanner":
        print("that's my name")
    elif command == "start_timer":
        tasks.add(asyncio.create_task(timer(command_dict["dur"])))
    else:
        print(f"unrecognized command: {command}")

    # add this function to new tasks so that another command can be processed
    tasks.add(asyncio.create_task(handle_command(input_queue)))

    return tasks


async def subprocess_main(input_queue):
    """Process all tasks until there are no more pending completion.

    Completed tasks may result in one or many new tasks being created.
    """
    pending = {asyncio.create_task(handle_command(input_queue))}
    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for coro in done:
            if coro_result := coro.result():
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
    # not sure if start method must be 'spawn' for this simple non-frozen example code
    aiomultiprocess.set_start_method("spawn")
    asyncio.run(main())
