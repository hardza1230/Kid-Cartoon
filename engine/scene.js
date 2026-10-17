export function sceneAt(d,t){return d.scenes.find(s=>t>=s.start&&t<s.end)||d.scenes.at(-1)}
export function frameAt(s,t){return s.frames[Math.floor(Math.max(0,t-s.start)*s.rate)%s.frames.length]}
export function validate(d){let end=0;for(const s of d.scenes){if(s.start!==end||s.end<=s.start)throw Error('Invalid timeline');end=s.end;for(const f of s.frames)if(!Number.isInteger(f)||f<0||f>=d.sprite.columns*d.sprite.rows)throw Error('Invalid sprite frame')}if(end!==d.duration)throw Error('Timeline duration mismatch');return true}
