/*
minimal local web server
h2kyeong, 2025. 8. 29.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/stat.h>


void fatal (const char *msg) {
	perror(msg);
	exit(1);
}

ssize_t write_all(int fd, const void *buf, size_t count) {
	const char *p = buf;
	size_t left = count;
	while (left > 0) {
		ssize_t written = write(fd, p, left);
		if (written < 0) {
			if (errno == EINTR) continue;
			return -1;
		}
		left -= written;
		p += written;
	}
	return count;
}



int port = 8080;
char *DATA_DIR = ".";

struct sockaddr_in address;
int server_fd, client_fd;
socklen_t addrlen;

int setup_server (){
	memset(&address, 0, sizeof(address));
	address.sin_family = AF_INET;
	address.sin_addr.s_addr = INADDR_ANY;
	address.sin_port = htons(port);
	addrlen = sizeof(address);
	server_fd = socket(AF_INET, SOCK_STREAM, 0);
	if (server_fd < 0)
		fatal("socket creation failed.");
	if (bind( server_fd, (struct sockaddr *)&address, addrlen ) < 0)
		fatal("bind failed.");
	if (listen( server_fd, 3 ) < 0)
		fatal("listen failed.");
	return 0;
}

struct data_t {
	char buffer[4096];
	char header[256];
	char response[(1<<16)];
	char path[1024];
	char filepath[1024];
};

struct data_t *data;

int send_file (const char* content_type){
	FILE *fin = fopen(data->filepath, "rb");
	if (!fin) return 1;
	size_t response_length = fread(data->response, 1, sizeof(data->response), fin);
	fclose(fin);
	
	int header_length = snprintf(data->header, sizeof(data->header),
		"HTTP/1.1 200 OK\r\n"
		"Content-Type: %s\r\n"
		"Content-Length: %zu\r\n\r\n",
		content_type, response_length);
	write_all(client_fd, data->header, header_length);
	write_all(client_fd, data->response, response_length);
	fputs(data->header, stdout);
	return 0;
}

int get_path (){
	int sp1 = 0;
	while (sp1 < sizeof(data->buffer)){
		if (data->buffer[sp1] == ' ') break;
		else sp1++;
	}
	if (sp1 >= sizeof(data->buffer))
		return 1;
	int sp2 = sp1+1;
	while (sp2 < sizeof(data->buffer)){
		if (data->buffer[sp2] == ' ') break;
		else sp2++;
	}
	if (sp2 >= sizeof(data->buffer))
		return 1;
	int path_length = sp2-sp1-1;
	if (path_length <= 0) return 1;
	if (path_length > sizeof(data->path)-1)
		path_length = sizeof(data->path)-1;
	memset(data->path, 0, path_length+1);
	memcpy(data->path, data->buffer+sp1+1, path_length);
	data->path[path_length] = 0;
	return 0;
}



int process_request (){
	if (get_path())
		fatal("parse_path encountered an error.");
	
	if (data->buffer[0] == 'G'){
		int len;
		memset(data->filepath, 0, sizeof(data->filepath));
		snprintf(data->filepath, sizeof(data->filepath), "%s%s", DATA_DIR, data->path);
		
		struct stat file_stat;
		if (stat(data->filepath, &file_stat))
			return 1;
		if (S_ISDIR(file_stat.st_mode)){
			len = strlen(data->filepath);
			snprintf(data->filepath+len, sizeof(data->filepath)-len, "%s", "/index.html");
			if (stat(data->filepath, &file_stat))
				return 1;
		}
		if (!S_ISREG(file_stat.st_mode))
			return 1;
		
		len = strlen(data->filepath);
		if (len >= 5 && strcmp(data->filepath + (len - 5), ".html") == 0)
			return send_file("text/html");
		if (len >= 4 && strcmp(data->filepath + (len - 4), ".css") == 0)
			return send_file("text/css");
		if (len >= 4 && strcmp(data->filepath + (len - 4), ".png") == 0)
			return send_file("image/png");
		if (len >= 4 && strcmp(data->filepath + (len - 4), ".jpg") == 0)
			return send_file("image/jpeg");
		if (len >= 4 && strcmp(data->filepath + (len - 4), ".svg") == 0)
			return send_file("image/svg+xml");
		if (len >= 3 && strcmp(data->filepath + (len - 3), ".js") == 0)
			return send_file("text/javascript");
		return 1;
	}
	return 0;
}

int main (int argc, char *argv[]) {
	int opt;
	while ((opt = getopt(argc, argv, "p:")) >= 0){
		switch(opt){
			case 'p':
				port = atoi(optarg);
		}
	}
	printf("Server listening on port %d\n", port);
	
	setup_server();
	
	data = (struct data_t *)malloc(sizeof(struct data_t));
	if (data == 0) fatal("memory allocation failed.");
	
	while (1){
		client_fd = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen);
		if (client_fd < 0)
			fatal("accepting socket failed");

		memset(data->buffer, 0, sizeof(data->buffer));
		int len = read(client_fd, data->buffer, sizeof(data->buffer));
		if (len < 0) {
			fatal("reading request failed");
		}
		fputs(data->buffer, stdout);
		
		memset(data->response, 0, sizeof(data->response));
		if (process_request())
			write_all(client_fd, "HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n", 57);
		
		close(client_fd);
	}
	return 0;
}
