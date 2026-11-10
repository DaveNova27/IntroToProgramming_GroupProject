// Jobs one after the other: a click that comes while a request is still running waits for it
// instead of being dropped. Pure, no page and no game rules (spec calm-panels).

export function createSerial() {
  let tail = Promise.resolve();
  // run(job): the job starts when all earlier jobs are done, whether they worked or failed.
  const run = (job) => {
    const result = tail.then(job, job);
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
  return { run, once };
}
