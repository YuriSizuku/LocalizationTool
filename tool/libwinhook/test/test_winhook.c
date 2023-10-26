#include <stdio.h>
#include <assert.h>

#define WINHOOK_IMPLEMENTATION
#define WINHOOK_NOINLINEHOOK
#define WINHOOK_USESHELLCODE
#include "winhook.h"

void test_patchpattern()
{
	printf("\n## test_patchpattern\n");
	char pattern[256];
	char tmp[256];
	uint8_t v1 = 1;
	uint32_t v2 = 2;
	int res = 0;

	printf("v1(%p)=%x v2(%p)=%x\n", &v1, v1, &v2, v2);
	strcpy(pattern, "# test winhook_patchmemorypattern\n");
	res = sprintf(tmp, "%p:ff\r\n", &v1);
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:12 ab ; %p :CD \n", &v2, (void*)((size_t)&v2+2));
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:09\r\n", (void*)((size_t)&v2 + 3));
	strcat(pattern, tmp);
	puts(pattern);
	res = winhook_patchmemorypattern(pattern);
	printf("v1(%p)=%x v2(%p)=%x\n", &v1, v1, &v2, v2);
	assert(res == 5);
	assert(v1 == 0xff);
	assert(v2 == 0x09cdab12);
}

void test_patch1337() 
{
	printf("\n## test_patch1337\n");
	char pattern[256] = {0};
	char tmp[256];
	uint8_t v1 = 1;
	uint32_t v2 = 2;
	int res = 0;
	size_t base = 0;

	printf("v1(%p)=%x v2(%p)=%x imagebase=%p\n", &v1, v1, &v2, v2, 
		(void*)winhook_getimagebase(GetCurrentProcess()));
	strcpy(pattern, ">test.exe\n");
	res = sprintf(tmp, "%p:%02X->ff\r\n", (void*)((size_t)&v1 - base),(uint8_t)v1);
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:%02x->12;", (void*)((size_t)&v2 - base), (uint8_t)(v2 & 0xff));
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:%02X->ab\n", (void*)((size_t)&v2 - base + 1), (uint8_t)(v2 >> 8) & 0xff);
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:%02X->CD\r", (void*)((size_t)&v2 - base + 2), (uint8_t)(v2 >> 16) & 0xff);
	strcat(pattern, tmp);
	res = sprintf(tmp, "%p:%02X->09\n", (void*)((size_t)&v2 - base + 3), (uint8_t)(v2 >> 24) & 0xff);
	strcat(pattern, tmp);
	puts(pattern);
	res = winhook_patchmemory1337(pattern, 0, FALSE);
	printf("v1(%p)=%x v2(%p)=%x\n", &v1, v1, &v2, v2);
	assert(res == 5);
	assert(v1 == 0xff);
	assert(v2 == 0x09cdab12);
}

void test_patchips() 
{
	printf("\n## test_patchips\n");
	char pattern[256];
	uint8_t v1 = 1;
	uint32_t v2 = 2;
	int res = 0;
	size_t base = (size_t)&v1;

	printf("v1(%p)=%x v2(%p)=%x\n", &v1, v1, &v2, v2);
	strncpy(pattern, "PATCH", 5);
	uint8_t* p = pattern + 5;
	*p++ = 0; *p++ = 0; *p++ = 0; // offset1
	*p++ = 0; *p++ = 1;// size1
	*p++ = 0xff; // patch1
	size_t offset = (size_t)&v2 - (size_t)&v1;
	*p++ = (offset >> 16) & 0xff; *p++ = (offset >> 8) & 0xff;  *p++ = offset&0xff;   // offset2
	*p++ = 0; *p++ = 4; // size2
	*p++ = 0x12; *p++ = 0xab; *p++ = 0xcd; *p++ = 0x09; // patch2
	strncpy(p, "EOF", 3);
	puts(pattern);
	res = winhook_patchmemoryips(pattern, base);
	printf("v1(%p)=%x v2(%p)=%x\n", &v1, v1, &v2, v2);
	assert(res == 5);
	assert(v1 == 0xff);
	assert(v2 == 0x09cdab12);
}

void test_searchpattern()
{
	printf("\n## test_searchpattern\n");
	char target[] = "\x20\x21\x22\x34\x22\x33\x44\x00";
	char* pattern = "22 34??3?\0";
	size_t matchsize = 0;
	void* matchaddr = NULL;
	matchaddr = winhook_searchmemory(target, sizeof(target), pattern, &matchsize);
	printf("winhook_searchmemory matchaddr=%p, matchsize=0x%zx\n", matchaddr, matchsize);
	matchaddr = winhook_searchmemoryex(GetCurrentProcess(), target, sizeof(target), pattern, &matchsize);
	printf("winhook_searchmemoryex matchaddr=%p, matchsize=0x%zx\n", matchaddr, matchsize);
}

void test_searchpattern2()
{
	printf("\n## test_searchpattern2\n");
	char target[] = "\x8B\x4D\xF8\x83\x61\x70\xFD\xC9\xC3\x8B\xFF\x55\x8B\xEC\x6A\x04\x6A\x00\xFF\x75\x08\x6A\x00\xE8\x9A\xFF\xFF\xFF\x83\xC4\x10\x5D\x00";
	char* pattern = "55 8b ec 6a 04 6a 00 ff 75 08 6a 00 e8";
	size_t matchsize = 0;
	void* matchaddr = NULL;
	matchaddr = winhook_searchmemory(target, sizeof(target), pattern, &matchsize);
	printf("winhook_searchmemory matchaddr=%p, matchsize=0x%zx\n", matchaddr, matchsize);
	matchaddr = winhook_searchmemoryex(GetCurrentProcess(), target, sizeof(target), pattern, &matchsize);
	printf("winhook_searchmemoryex matchaddr=%p, matchsize=0x%zx\n", matchaddr, matchsize);
}

void test_startexeinject()
{
	printf("\n## test_startexeinject\n");
	DWORD pid = winhook_startexeinject("hello.exe", NULL, "hello.dll");
}

void test_windyn()
{
#ifdef WINDYN_IMPLEMENTATION
#endif
}

int main(int argc, char *argv[])
{
	test_patchpattern();
	test_patch1337();
	test_patchips();
	test_searchpattern();
	test_searchpattern2();
	test_startexeinject();
	test_windyn();
	return 0;
}