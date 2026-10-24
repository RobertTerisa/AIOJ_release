#include<bits/stdc++.h>
using namespace std;
int n,t,a[21],b[21],l,tot;
bool dfs(int k,int sum,int p)//分别是上一根小木棍的编号、当前边已拼长度、第几条边
{
	if(p==4)return true;//剪枝 2：前三边拼好了，到第四边就不用拼了
	for(int i=k+1;i<=n;i++)
	{
		if(sum+a[i]<l&&!b[i])//当前长度和小于要拼边长且小木棍没用过
		{
			b[i]=1;
			if(dfs(i,sum+a[i],p))
				return true;
			b[i]=0;
		}
		if(sum+a[i]==l&&!b[i])//这根木棍加上去就拼好了一边的情况
		{
			b[i]=1;
			if(dfs(0,0,p+1))//这里 k 为 0 是因为我的循环是从 k+1 开始搜的
				return true;
			b[i]=0;
		}
	}
	return false;//记得打这个不然 RE
}
int main()
{
	scanf("%d",&t);
	for(int phi=1;phi<=t;phi++)
	{
		scanf("%d",&n);
		for(int i=1;i<=n;i++)
			b[i]=0;
		tot=0;
		for(int i=1;i<=n;i++)
		{
			scanf("%d",&a[i]);
			tot+=a[i];
		}
		sort(a+1,a+n+1);
		reverse(a+1,a+n+1);//剪枝 1：由大到小排序
		l=tot/4;
		if(tot%4||a[1]>l)//特判：如果总长度和不为 4 的倍数，或者这里面最长的木棍的长度大于了要拼的边长，直接输出 no
		{
			printf("no\n");
			continue;
		}
		if(dfs(0,0,1))printf("yes\n");//写成 bool 类型的函数作为判断的条件
		else printf("no\n");
	}
	return 0;
}
