FROM nvcr.io/nvidia/isaac-sim:5.0.0

ARG UNITREE_SIM_COMMIT=e30c25b1dffdf92ada1d6c8c1fe9a47bdde0fecc
ENV DEBIAN_FRONTEND=noninteractive

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git git-lfs openssl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install --system

WORKDIR /opt
RUN git clone https://github.com/isaac-sim/IsaacLab.git \
    && cd IsaacLab \
    && git checkout v2.2.0 \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -e source/isaaclab \
       -e source/isaaclab_assets -e source/isaaclab_mimic -e source/isaaclab_rl \
       -e source/isaaclab_tasks

RUN git clone https://github.com/eclipse-cyclonedds/cyclonedds.git -b releases/0.10.x \
    && cmake -S cyclonedds -B cyclonedds/build -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds/install \
    && cmake --build cyclonedds/build --target install -j2
ENV CYCLONEDDS_HOME=/opt/cyclonedds/install
ENV LD_LIBRARY_PATH=/opt/cyclonedds/install/lib:${LD_LIBRARY_PATH}

RUN git clone https://github.com/unitreerobotics/unitree_sdk2_python.git \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -e /opt/unitree_sdk2_python

RUN git clone https://github.com/unitreerobotics/unitree_sim_isaaclab.git \
    && cd unitree_sim_isaaclab \
    && git checkout ${UNITREE_SIM_COMMIT} \
    && git submodule update --init --depth 1 \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -r requirements.txt \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -e teleimager \
    && sed -i 's/type:.*/type: isaacsim/' teleimager/cam_config_server.yaml \
    && sed -i 's/image_shape:.*/image_shape: [480, 640]/' teleimager/cam_config_server.yaml \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -subj '/CN=embodied-book-labs' -keyout /opt/unitree_sim_isaaclab/key.pem \
       -out /opt/unitree_sim_isaaclab/cert.pem

WORKDIR /opt/unitree_sim_isaaclab
COPY docker/isaac/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["smoke"]
