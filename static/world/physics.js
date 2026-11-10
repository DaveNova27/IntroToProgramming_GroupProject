// Solid objects and walking. Pure functions, no drawing and no game rules.
// Taken unchanged from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures).

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

export function resolveMovement(position,delta,bounds,colliders,radius=.28){
  const target={
    x:clamp(position.x+delta.x,bounds.minX+radius,bounds.maxX-radius),
    y:clamp(position.y+delta.y,bounds.minY+radius,bounds.maxY-radius)
  };
  const direct=pointBlocked(target,colliders,radius);
  if(!direct)return {...target,blocked:false,collider:null};

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
