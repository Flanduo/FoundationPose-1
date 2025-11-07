docker rm -f foundationpose
DIR=/home/wyf/Projects/FoundationPose

xhost +  && docker run --gpus all --env NVIDIA_DISABLE_REQUIRE=1 -it --network=host --name foundationpose  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined -v $DIR:$DIR -v /home/wyf/Projects/FoundationPose/:/FoundationPose -v /mnt:/mnt -v /tmp/.X11-unix:/tmp/.X11-unix -v /tmp:/tmp  --ipc=host -e DISPLAY=${DISPLAY} -e GIT_INDEX_FILE Grsam:latest bash -c "cd $DIR && bash"