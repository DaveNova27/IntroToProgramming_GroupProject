// Solid objects and walking. Pure functions, no drawing and no game rules.
// Taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures). Changed for smooth-walk: a step that runs
// into an object glides along its edge (pushOut, glide) instead of stopping (specs/smooth-walk.md).

const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));

export function pointBlocked(point,colliders,radius=.28){
  for(const collider of colliders){
    if(collider.disabled)continue;
    if(collider.shape==="circle"){
      if(Math.hypot(point.x-collider.x,point.y-collider.y)<collider.radius+radius)return collider;
      continue;
    }
    const nearestX=clamp(point.x,collider.x,collider.x+collider.width);
    const nearestY=clamp(point.y,collider.y,collider.y+collider.height);
    if(Math.hypot(point.x-nearestX,point.y-nearestY)<radius)return collider;
  }
  return null;
}

// HEAD_ON: a step this close to the middle of a round object counts as straight at it.
// LEAN: how far (share of the step) such a step leans to one side, so that the push below leads around.
// GAP: the pushed point stays this far outside the edge, so that it is not blocked again.
const HEAD_ON=.05,LEAN=.3,GAP=.001;

// Moves a point that went into an object back to its edge, the shortest way out.
// null if the point is inside a rectangle (no way out is known there).
function pushOut(point,collider,radius=.28){
  const round=collider.shape==="circle";
  const nearX=round?collider.x:clamp(point.x,collider.x,collider.x+collider.width);
  const nearY=round?collider.y:clamp(point.y,collider.y,collider.y+collider.height);
  const dx=point.x-nearX,dy=point.y-nearY,away=Math.hypot(dx,dy);
  if(away<1e-6)return null;
  const edge=(round?collider.radius:0)+radius+GAP;
  return {x:nearX+dx/away*edge,y:nearY+dy/away*edge};
}

// Where a step that runs into an object ends if it glides along the object's edge.
// Straight at the middle of a round object the step leans to one side first (always the same side
// for the same step: no randomness), otherwise it would be pushed straight back.
function glide(position,delta,collider,radius){
  let target={x:position.x+delta.x,y:position.y+delta.y};
  if(collider.shape==="circle"){
    const step=Math.hypot(delta.x,delta.y);
    const toX=collider.x-position.x,toY=collider.y-position.y,distance=Math.hypot(toX,toY);
    const side=delta.x*toY-delta.y*toX;
    if(step>0&&Math.abs(side)<step*distance*HEAD_ON){
      const sign=side>0?-1:1; // lean away from the middle, never towards it
      target={x:target.x-delta.y*LEAN*sign,y:target.y+delta.x*LEAN*sign};
    }
  }
  return pushOut(target,collider,radius);
}

export function resolveMovement(position,delta,bounds,colliders,radius=.28){
  const fit=(point)=>({
    x:clamp(point.x,bounds.minX+radius,bounds.maxX-radius),
    y:clamp(point.y,bounds.minY+radius,bounds.maxY-radius)
  });
  const target=fit({x:position.x+delta.x,y:position.y+delta.y});
  const direct=pointBlocked(target,colliders,radius);
  if(!direct)return {...target,blocked:false,collider:null};

  const along=glide(position,delta,direct,radius);
  if(along){
    const slide=fit(along);
    // only if it still gets on in the walking direction; a glide backwards would lead into a corner
    const gain=(slide.x-position.x)*delta.x+(slide.y-position.y)*delta.y;
    if(gain>0&&!pointBlocked(slide,colliders,radius))return {...slide,blocked:true,collider:direct};
  }

  const slideX={x:target.x,y:position.y};
  if(Math.abs(delta.x)>.0001&&!pointBlocked(slideX,colliders,radius))return {...slideX,blocked:true,collider:direct};
  const slideY={x:position.x,y:target.y};
  if(Math.abs(delta.y)>.0001&&!pointBlocked(slideY,colliders,radius))return {...slideY,blocked:true,collider:direct};
  return {x:position.x,y:position.y,blocked:true,collider:direct};
}

export function nearestFreePoint(point,bounds,colliders,radius=.28){
  const origin={x:clamp(point.x,bounds.minX+radius,bounds.maxX-radius),y:clamp(point.y,bounds.minY+radius,bounds.maxY-radius)};
  if(!pointBlocked(origin,colliders,radius))return origin;
  for(let ring=1;ring<=18;ring++){
    const distance=ring*.18;
    for(let step=0;step<16;step++){
      const angle=step*Math.PI/8,candidate={x:clamp(origin.x+Math.cos(angle)*distance,bounds.minX+radius,bounds.maxX-radius),y:clamp(origin.y+Math.sin(angle)*distance,bounds.minY+radius,bounds.maxY-radius)};
      if(!pointBlocked(candidate,colliders,radius))return candidate;
    }
  }
  return origin;
}
