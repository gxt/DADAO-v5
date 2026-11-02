/* Dynamic-loader probe (TESTCASES-046t dynamic round, ISS-258 follow-up).
 *
 * Prints the auxv entries the loader must supply for a dynamically linked
 * DADAO executable (contract-dynlink.md §6.3) and the /proc/self/maps line
 * that carries the interpreter.  The evidence script compares these values
 * with the ELF headers it parses itself:
 *
 *   AT_ENTRY == e_entry, AT_PHNUM == e_phnum, AT_PHENT == e_phentsize,
 *   AT_PHDR != 0, AT_BASE != 0 and page aligned (interpreter load bias),
 *   a maps line naming the interpreter.
 *
 * Exit 0 when the auxv entries are present and a maps line matches, 3 otherwise
 * (the script asserts the exit status, so a missing entry cannot look green).
 */
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/auxv.h>
#include <unistd.h>

int main(void)
{
	unsigned long phdr = getauxval(AT_PHDR);
	unsigned long entry = getauxval(AT_ENTRY);
	unsigned long base = getauxval(AT_BASE);
	unsigned long phnum = getauxval(AT_PHNUM);
	unsigned long phent = getauxval(AT_PHENT);
	char line[512];
	int maps_found = 0;
	FILE *fp;

	printf("AT_PHDR=0x%lx\n", phdr);
	printf("AT_ENTRY=0x%lx\n", entry);
	printf("AT_BASE=0x%lx\n", base);
	printf("AT_PHNUM=%lu\n", phnum);
	printf("AT_PHENT=%lu\n", phent);

	fp = fopen("/proc/self/maps", "r");
	if (!fp) {
		printf("MAPS=open-failed\n");
		return 3;
	}
	while (fgets(line, sizeof line, fp)) {
		if (strstr(line, "ld-musl-dadao.so.1")) {
			line[strcspn(line, "\n")] = '\0';
			printf("MAPS=%s\n", line);
			maps_found = 1;
			break;
		}
	}
	fclose(fp);

	if (base == 0 || base % 4096 || phdr == 0 || entry == 0 || !maps_found)
		return 3;
	return 0;
}
