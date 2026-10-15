#include<iostream>
#include<cstdio>
#include<cstring>
#include<algorithm>
using namespace std;
#define mx 100100//要大于(n*n)*(6*n-2)解释见主函数 
long long sum=0;//方案总数 
int nn;
struct out{
	int ans[14];
}ss[100000];//记录答案的数组 
struct DLX{
	int n,m,cnt;//矩阵的长，宽，点的数量
	int l[mx],r[mx],u[mx],d[mx],row[mx],col[mx];//每个点的左，右，上下，行，列信息 
	int h[mx];//每行的头结点 
	int s[mx];//每列的结点数 
	int ansk[mx];//选了ansk[] 
	void init(int _n,int _m){
		n=_n,m=_m;
		int i;
		for(i=0;i<=m;i++){
			r[i]=i+1;l[i]=i-1;u[i]=d[i]=i;
		}
		r[m]=0;//m右边是0 
		l[0]=m;//0左边是m 
		memset(h,-1,sizeof(h));
		memset(s,0,sizeof(s));
		cnt=m+1;//开始时有m个结点（0结点和各列头结点） 
	}//初始化，生成每列的头
	inline void link(int R,int C){
		s[C]++;
		row[cnt]=R;
		col[cnt]=C;
		u[cnt]=C;
		d[cnt]=d[C];
		u[d[C]]=cnt;
		d[C]=cnt;
		if(h[R]<0)h[R]=r[cnt]=l[cnt]=cnt;//该行没有别的点,把第一个加入的点作为该行的行头结点 
		else{
			r[cnt]=h[R];
			l[cnt]=l[h[R]];
			r[l[h[R]]]=cnt;
			l[h[R]]=cnt;
		}
		cnt++;
	}//在r行c列插入点
	inline void remove(int c){
		r[l[c]]=r[c],l[r[c]]=l[c];
		for(int i=d[c];i!=c;i=d[i]){
			for(int j=r[i];j!=i;j=r[j]){
				u[d[j]]=u[j];
				d[u[j]]=d[j];
				s[col[j]]--;
			}
		}
	}//删除c列和c列上有点的行
	inline void resume(int c){
		for(int i=u[c];i!=c;i=u[i]){
			for(int j=l[i];j!=i;j=l[j]){
				u[d[j]]=j;
				d[u[j]]=j;
				s[col[j]]++;
			}
		}
		r[l[c]]=c;
		l[r[c]]=c;
	}//恢复c列和c列上有点的行
	void dance(int deep){
		if(r[0]>nn){//前nn列都已删除表示已经放完了 
		sum++;
			int x,y;
			for(register int i=0;i<deep;i++){
			x=ansk[i]%nn;
			y=(ansk[i]-1)/nn+1;
			if(x==0)x=nn;
			ss[sum].ans[x]=y;
			}
		return;
		}
		int c=r[0];
		register int i,j;
		for(i=r[0];i<=nn;i=r[i])if(s[i]<s[c])c=i;//找到点最少的列，只需看前nn列是否删完 
		remove(c);
		for(i=d[c];i!=c;i=d[i]){
			ansk[deep]=row[i];
			for(j=r[i];j!=i;j=r[j]) remove(col[j]);
			dance(deep+1);
			for(j=l[i];j!=i;j=l[j]) resume(col[j]);
		}
		resume(c); 
		return ;
	}
}dlx;
bool cap(out a,out b){
	int i=1;
	while(a.ans[i]==b.ans[i]&&i<=nn){
		i++;
	}
	return a.ans[i]<b.ans[i];
}//根据题目要求找出前3种解法 
int main(){
	scanf("%d",&nn);
	dlx.init(nn*nn,6*nn-2);
	//一共n*n格对应n*n行
	//对于第m列
	//若[1,n]对应在第m行放皇后 
	//若[n+1,2*n]对应在第m-n列放皇后 
	//若[2*n+1,4*n-1]对应在第m-2*n“\”斜行放皇后 （共2*n-1个“\”斜行） 
	//若[4*n,6*n-2]对应在第m-4*n+1“/”斜行放皇后（共2*n-1个“/”斜行） 
	int x;	
	register int i,j;
	int o=0;
	for(i=1;i<=nn;i++){
	 	for(j=1;j<=nn;j++){
	 	o++;//第o行对应坐标(o/n+1,o%n) 
	 	dlx.link(o,i);
	 	dlx.link(o,j+nn);
	 	dlx.link(o,i-j+3*nn);
	 	dlx.link(o,i+j+4*nn-2);
		 }
	 }
	dlx.dance(0);
	sort(ss+1,ss+1+sum,cap);
	for(i=1;i<=3;i++){
		for(j=1;j<=nn;j++)printf("%d ",ss[i].ans[j]);
		printf("\n");
	}
	printf("%lld",sum);
	return 0;
}
