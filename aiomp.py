import asyncio
from functools import wraps
from queue import Empty

import aiomultiprocess


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


class BreakLoop(Exception):
    pass


# TODO probably want to wrap into a class to handle shared state


async def timer(time_remaining):
    """Start a countdown timer with the given number of seconds"""
    while time_remaining > 0:
        print(time_remaining)
        await asyncio.sleep(1)
        time_remaining -= 1
    print("TIMER COMPLETE")


def loop_until_break(func):
    """Wait for a command in the queue and then process it.

    Returns new tasks which should be awaited together.
    Includes itself in tasks unless quitting so that the next
    command can be processed.
    """

    @wraps(func)
    async def _foo(input_queue):
        # Regular mp queue is not awaitable and thus will block, so need to poll it then
        # sleep to prevent blocking other coroutines. Should replace this with a
        # process/thread safe + asyncio compatible queue
        command_dict = None
        while not command_dict:
            try:
                command_dict = input_queue.get_nowait()
            except Empty:
                await asyncio.sleep(0.01)

        tasks = func(command_dict) 
        # add this function to new tasks so that another command can be processed
        tasks.add(asyncio.create_task(_foo(input_queue)))
        return tasks

    return _foo


@loop_until_break
def handle_command(command_dict):
    tasks = set()

    # process command
    command = command_dict["command"]
    if command == "quit":
        raise BreakLoop()
    if command == "tanner":
        print("that's my name")
    elif command == "start_timer":
        timer_task = asyncio.create_task(timer(command_dict["dur"]))
        timer_task.set_name(f"Timer-{timer_task.get_name()}")
        tasks.add(timer_task)
    else:
        print(f"unrecognized command: {command}")

    return tasks


async def cancel_remaining_tasks(remaining_tasks):
    print("cancelling any remaining tasks")
    for task in remaining_tasks:
        task.cancel()
        try:
            await task
        except asyncio.exceptions.CancelledError:
            print(f"Cancelled task: {task.get_name()}")


async def subprocess_main(input_queue):
    """Process all tasks until there are no more pending completion.

    Completed tasks may result in one or many new tasks being created.
    """
    pending = {asyncio.create_task(handle_command(input_queue))}
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for coro in done:
            try:
                new_tasks = coro.result()
            except BreakLoop:
                await cancel_remaining_tasks(pending)
                pending.clear()
            else:
                if new_tasks:
                    pending |= new_tasks
    print("subprocess quitting")


async def main():
    subprocess_input_queue = aiomultiprocess.core.get_manager().Queue()
    async_process = aiomultiprocess.Process(target=subprocess_main, args=(subprocess_input_queue,))
    async_process.start()
    await asyncio.gather(handle_user_input(subprocess_input_queue), async_process.join())


if __name__ == "__main__":
    # not sure if start method must be 'spawn' for this simple non-frozen example code
    aiomultiprocess.set_start_method("spawn")
    asyncio.run(main())
