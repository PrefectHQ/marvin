def create_env_file(directory, env_variables):
    file_path = directory + "/.env"
    try:
        with open(file_path, "w") as env_file:
            for variable in env_variables:
                key, value = variable
                env_file.write("{}={}\n".format(key, value))
    except IOError as e:
        print("Error creating .env file:", str(e))
    else:
        print("Successfully created .env file:", file_path)
