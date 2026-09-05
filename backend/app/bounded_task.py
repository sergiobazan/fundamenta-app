"""Run CPU/network-heavy work with a hard wall-clock deadline, including PDF parsing."""

import logging
import multiprocessing


def _execute(sender, function, args):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        sender.send((True, function(*args)))
    except Exception as error:
        sender.send((False, f"{type(error).__name__}: {error}"))
    finally:
        sender.close()


def run_bounded(function, args, timeout):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_execute, args=(sender, function, args))
    try:
        process.start()
        sender.close()
        if not receiver.poll(timeout):
            raise TimeoutError("La etapa documental superó su tiempo máximo; se reintentará")
        try:
            success, result = receiver.recv()
        except EOFError as error:
            raise RuntimeError("El proceso documental terminó sin devolver resultado") from error
        if not success:
            raise RuntimeError(result)
        return result
    finally:
        if process.pid is not None:
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            process.close()
        sender.close()
        receiver.close()
