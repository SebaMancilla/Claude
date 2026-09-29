from cam import *
CAMS={
1:dict(f=536.6782,C=[-3.5028,1.4642,-6.3767],yaw=0.7386,pitch=-0.0309,roll=-0.0161),
2:dict(f=529.6271,C=[3.7115,1.5052,-7.6194],yaw=-0.2775,pitch=0.0436,roll=-0.013),
3:dict(f=954.265,C=[2.297,1.314,-7.269],yaw=-0.091,pitch=-0.016,roll=-0.019),
}
def get(i):
    p=CAMS[i]; return Cam(p['f'],p['C'],p['yaw'],p['pitch'],p['roll'])
def triangulate(obs):
    # obs: list of (cam, x, y) -> least squares closest point
    A=np.zeros((3,3)); b=np.zeros(3)
    for c,x,y in obs:
        d=c.ray(x,y); d/=np.linalg.norm(d); M=np.eye(3)-np.outer(d,d); A+=M; b+=M@c.C
    return np.linalg.solve(A,b)
