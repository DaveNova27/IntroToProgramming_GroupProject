// Jobs one after the other: a click that comes while a request is still running waits for it
// instead of being dropped. Pure, no page and no game rules (spec calm-panels).
// Epochs (spec stale-tick): renew() says the run was replaced. A job queued before that and not
// started yet is dropped; a job already running can ask stale() before it takes its answer over.

export function createSerial() {
  let tail = Promise.resolve();
  let epoch = 0;
  // run(job): the job starts when all earlier jobs are done, whether they worked or failed.
  // It gets stale(): true once renew() was called after the job was queued.
  const run = (job) => {
    const at = epoch;
    const stale = () => at !== epoch;
    const start = () => (stale() ? undefined : job(stale));
    const result = tail.then(start, start);
    tail = result.then(() => {}, () => {});
    return result;
  };
  // once(key, job): like run, but ignored while a job with the same key is waiting or running
  // (the one-second tick must not pile up behind a slow request).
  const waiting = new Set();
  const once = (key, job) => {
    if (waiting.has(key)) return Promise.resolve();
    waiting.add(key);
    return run(job).finally(() => waiting.delete(key));
  };
  const renew = () => {
    epoch++;
  };
  return { run, once, renew };
}
